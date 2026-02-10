"""
Structured Data Extraction Module
Extracts logistics shipment fields using LLM or regex-based extraction.
"""

import os
import re
import json
from typing import Optional, List, Tuple

from openai import OpenAI
from dotenv import load_dotenv

from document_processor import get_raw_text
from models import ExtractResponse, ShipmentData

load_dotenv()


def get_openai_client() -> Optional[OpenAI]:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or api_key == "your-openai-api-key-here":
        return None
    try:
        return OpenAI(api_key=api_key)
    except Exception as e:
        print(f"[Extractor] Failed to create OpenAI client: {e}")
        return None


EXTRACTION_PROMPT = """You are an expert logistics data extractor. Extract the following structured fields from the document text provided.

Fields to extract:
- shipment_id: Any shipment/load/order/reference number
- shipper: The shipping company or origin party
- consignee: The receiving party or destination company
- pickup_datetime: Pickup date and time (use ISO format if possible)
- delivery_datetime: Delivery date and time (use ISO format if possible)
- equipment_type: Type of equipment (e.g., Dry Van, Reefer, Flatbed, 53' Trailer)
- mode: Transportation mode (e.g., FTL, LTL, Intermodal, Air)
- rate: The freight rate or total charges (numeric value)
- currency: Currency of the rate (e.g., USD, CAD, EUR)
- weight: Total weight of the shipment (include unit if available)
- carrier_name: Name of the carrier/trucking company

RULES:
1. Extract ONLY information explicitly stated in the document.
2. Use null for any field not found in the document.
3. For dates, try to use ISO 8601 format (YYYY-MM-DDTHH:MM:SS) when possible.
4. For rates, extract the numeric value as a string (e.g., "2500.00").
5. Return ONLY valid JSON, no additional text.

Respond with a JSON object containing exactly these fields. Example:
{
  "shipment_id": "SH-12345",
  "shipper": "ABC Corp",
  "consignee": "XYZ Inc",
  "pickup_datetime": "2024-01-15T08:00:00",
  "delivery_datetime": "2024-01-17T14:00:00",
  "equipment_type": "53' Dry Van",
  "mode": "FTL",
  "rate": "2500.00",
  "currency": "USD",
  "weight": "42000 lbs",
  "carrier_name": "FastFreight LLC"
}
"""

# ── Regex-based Fallback Extraction ─────────────────────────────────

def _is_junk_value(val: str) -> bool:
    """
    Check if an extracted value looks like garbage (table header, column names, etc.).
    """
    if not val or len(val.strip()) < 2:
        return True

    val_lower = val.lower().strip()

    # Skip section headers
    skip_words = {
        "information", "details", "section", "data", "summary",
        "n/a", "na", "none", "null", "tbd", "---", "===",
    }
    if val_lower in skip_words:
        return True

    if val.startswith("---") or val.startswith("==="):
        return True

    # Reject dash-only values like "-", "- -", "--"
    if re.match(r'^[\s\-]+$', val):
        return True

    # If it contains multiple column-header-like words, it's a table header
    header_keywords = {
        "carrier", "mc", "phone", "equipment", "agreed", "amount",
        "size", "feet", "column", "field", "value", "type", "name",
        "address", "city", "state", "zip", "contact", "email", "fax",
    }
    words = set(val_lower.split())
    header_overlap = len(words & header_keywords)
    if header_overlap >= 3 and len(words) >= 4:
        return True

    # If it looks like a pipe-delimited table row header
    if "|" in val and val.count("|") >= 2:
        return True

    return False


def _find_value_after_label(text: str, label_patterns: List[str], multiline: bool = False) -> Optional[str]:
    """
    Find the value after a label in text.
    Handles formats like:
      Label: Value
      Label\nValue
      Label: Value (with extra info)
    Skips values that look like junk (section headers, table headers, etc.).
    """
    for pattern in label_patterns:
        flags = re.IGNORECASE | (re.MULTILINE if multiline else 0)
        match = re.search(pattern, text, flags)
        if match:
            val = match.group(1).strip()
            if _is_junk_value(val):
                continue
            return val[:150]
    return None


def _find_next_value_line(lines: List[str], start_idx: int, skip_count: int = 4) -> Optional[str]:
    """
    Starting from a header line, find the first data line below it.
    Skips separator lines (---), blank lines, and sub-header labels.
    """
    for j in range(start_idx + 1, min(start_idx + skip_count + 1, len(lines))):
        candidate = lines[j].strip()
        if not candidate:
            continue
        if candidate.startswith("---") or candidate.startswith("==="):
            continue
        if _is_junk_value(candidate):
            continue
        # Check if it's a "Name: Value" line
        name_match = re.match(r'^(?:name|company)\s*:\s*(.+)', candidate, re.IGNORECASE)
        if name_match:
            return name_match.group(1).strip()
        # Skip sub-labels like "Address:", "Contact:", "Phone:"
        if re.match(r'^(?:address|contact|phone|email|fax|city|state|zip)\s*:', candidate, re.IGNORECASE):
            continue
        return candidate
    return None


def _extract_with_regex(text: str) -> Tuple[dict, List[str]]:
    """
    Regex-based extraction as fallback when LLM is unavailable.
    Handles both label:value formats and table-based/PDF-extracted formats
    (including Ultraship TMS rate confirmations and BOLs).
    Returns (extracted_dict, extraction_notes).
    """
    result = {}
    notes = []
    text_upper = text.upper()
    text_lower = text.lower()
    lines = text.split("\n")

    # Pre-process: fix common PDF concatenation issues
    # e.g., "FTLShipping Date" -> "FTL Shipping Date", "USDPickup" -> "USD Pickup"
    cleaned_text = re.sub(r'(FTL|LTL)(Shipping|Delivery|Ship)', r'\1 \2', text)
    cleaned_text = re.sub(r'(USD)(Pickup|Drop)', r'\1 \2', cleaned_text)
    cleaned_text = re.sub(r'(usdev@\S+)(Dispatcher)', r'\1 \2', cleaned_text)
    cleaned_text = re.sub(r'(usdev@\S+)(Load)', r'\1 \2', cleaned_text)
    cleaned_lines = cleaned_text.split("\n")

    # ── Shipment ID ──
    id_patterns = [
        r'(?:reference|ref)\s*id\s*:?\s*([A-Za-z0-9][\w\-]{2,25})',
        r'load\s*id\s*:?\s*([A-Za-z0-9][\w\-]{2,25})',
        r'shipment\s*(?:id|#|no\.?|number)\s*:?\s*([A-Za-z0-9][\w\-]{2,25})',
        r'load\s*(?:#|no\.?|number)\s*:?\s*([A-Za-z0-9][\w\-]{2,25})',
        r'(?:bol|pro)\s*(?:#|no\.?|number)\s*:?\s*([A-Za-z0-9][\w\-]{2,25})',
        r'confirmation\s*(?:#|no\.?|number)\s*:?\s*([A-Za-z0-9][\w\-]{2,25})',
        r'order\s*(?:id|#|no\.?|number)\s*:?\s*([A-Za-z0-9][\w\-]{2,25})',
        r'(?:rate\s+)?conf(?:irmation)?\s*#?\s*:?\s*([A-Za-z0-9][\w\-]{2,25})',
    ]
    val = _find_value_after_label(text, id_patterns)
    if not val:
        # Try on cleaned text too
        val = _find_value_after_label(cleaned_text, id_patterns)
    if val:
        result["shipment_id"] = val

    # ── Shipper ──
    shipper_patterns = [
        r'shipper\s*(?:name)?\s*:\s*(.+?)(?:\n|$)',
        r'ship\s+from\s*:\s*(.+?)(?:\n|$)',
        r'origin\s*(?:name|company)?\s*:\s*(.+?)(?:\n|$)',
        r'pick\s*-?\s*up\s+(?:location|company|name)\s*:\s*(.+?)(?:\n|$)',
    ]
    val = _find_value_after_label(text, shipper_patterns)
    if not val:
        # Look for section header pattern (standard)
        for i, line in enumerate(lines):
            stripped = line.strip()
            if re.match(r'^(?:shipper|ship\s+from|origin)\s*(?:information|details)?\s*$', stripped, re.IGNORECASE):
                val = _find_next_value_line(lines, i, skip_count=5)
                break
    if not val:
        # Ultraship TMS format: "Pickup" section header (may be on its own line or concat'd)
        for i, line in enumerate(cleaned_lines):
            stripped = line.strip()
            if stripped.lower() == "pickup" or re.match(r'^pickup\s*$', stripped, re.IGNORECASE):
                val = _find_next_value_line(cleaned_lines, i, skip_count=3)
                break
        # Also check if "Pickup" appears at end of a concatenated line (e.g., "...USDPickup")
        if not val:
            for i, line in enumerate(cleaned_lines):
                if re.search(r'Pickup\s*$', line.strip()):
                    val = _find_next_value_line(cleaned_lines, i, skip_count=3)
                    break
    if not val:
        # TMS BOL format: "Shipper Consignee" on one line, data on next lines
        for i, line in enumerate(lines):
            stripped = line.strip()
            if re.match(r'^shipper\s+(?:consignee|receiver)', stripped, re.IGNORECASE):
                # Next line has shipper data (may include consignee data too)
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    # Handle format like "1.AAA ," or just "CompanyName,"
                    shipper_match = re.match(r'^(?:\d+\.)?\s*(.+?)\s*[,;]?\s*$', next_line)
                    if shipper_match:
                        val = shipper_match.group(1).strip().rstrip(",")
                break
    if val and not _is_junk_value(val):
        result["shipper"] = val[:100]

    # ── Consignee ──
    consignee_patterns = [
        r'consignee\s*(?:name)?\s*:\s*(.+?)(?:\n|$)',
        r'ship\s+to\s*:\s*(.+?)(?:\n|$)',
        r'deliver\s+to\s*:\s*(.+?)(?:\n|$)',
        r'receiver\s*(?:name)?\s*:\s*(.+?)(?:\n|$)',
        r'destination\s*(?:name|company)?\s*:\s*(.+?)(?:\n|$)',
    ]
    val = _find_value_after_label(text, consignee_patterns)
    if not val:
        # Standard section headers
        for i, line in enumerate(lines):
            stripped = line.strip()
            if re.match(r'^(?:consignee|ship\s+to|deliver\s+to|receiver|destination)\s*(?:information|details)?\s*$', stripped, re.IGNORECASE):
                val = _find_next_value_line(lines, i, skip_count=5)
                break
    if not val:
        # Ultraship TMS: "Drop" section header, then consignee data
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.lower() == "drop" or re.match(r'^drop\s*(?:off)?\s*$', stripped, re.IGNORECASE):
                val = _find_next_value_line(lines, i, skip_count=3)
                break
    if not val:
        # TMS BOL: look for "Shipper Consignee" header then parse second half of data
        for i, line in enumerate(lines):
            if re.match(r'^shipper\s+(?:consignee|receiver)', line.strip(), re.IGNORECASE):
                # Look for consignee data — often after a digit prefix like "1.xyz ,"
                # or on a line containing the destination address
                for j in range(i + 1, min(i + 5, len(lines))):
                    l = lines[j]
                    # Look for patterns like "Los Angeles, CA, USA1.xyz ,"
                    consignee_split = re.search(r'USA\d*\.?\s*(.+?)(?:\s*,\s*$|\s*$)', l)
                    if consignee_split:
                        val = consignee_split.group(1).strip().rstrip(",")
                        if val and len(val) > 1:
                            break
                break
    if val and not _is_junk_value(val):
        result["consignee"] = val[:100]

    # ── Dates ──
    date_formats = r'(?:\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\w+\s+\d{1,2},?\s+\d{4}|\d{4}-\d{2}-\d{2})'

    # Use cleaned_text for dates to catch concatenated "FTLShipping Date"
    search_text = cleaned_text

    pickup_patterns = [
        r'(?:shipping|pickup|pick[\s-]*up)\s*date\s*:?\s*(' + date_formats + r')',
        r'ship\s*date\s*:?\s*(' + date_formats + r')',
        r'pickup\s*(?:date|time|dt)?\s*:?\s*(' + date_formats + r')',
        r'loading\s*(?:date|time)?\s*:?\s*(' + date_formats + r')',
        r'earliest\s*pick\s*-?\s*up\s*:?\s*(' + date_formats + r')',
    ]
    val = _find_value_after_label(search_text, pickup_patterns)
    if val and not _is_junk_value(val):
        result["pickup_datetime"] = val.strip()

    delivery_patterns = [
        r'delivery\s*date\s*:?\s*(' + date_formats + r')',
        r'deliver(?:y)?\s*date\s*:?\s*(' + date_formats + r')',
        r'drop[\s-]*off\s*(?:date|time)?\s*:?\s*(' + date_formats + r')',
        r'latest\s*delivery?\s*:?\s*(' + date_formats + r')',
        r'(?:must|due|expected)\s*(?:deliver|arrival)\s*:?\s*(' + date_formats + r')',
    ]
    val = _find_value_after_label(search_text, delivery_patterns)
    if val and not _is_junk_value(val):
        result["delivery_datetime"] = val.strip()

    # Contextual date scan for remaining missing dates
    if "pickup_datetime" not in result:
        for i, line in enumerate(lines):
            if re.search(r'pick[\s-]*up|origin|loading|shipping\s*date|ship\s*date', line, re.IGNORECASE):
                date_match = re.search(date_formats, line)
                if date_match:
                    result["pickup_datetime"] = date_match.group(0).strip()
                    break
                if i + 1 < len(lines):
                    date_match = re.search(date_formats, lines[i + 1])
                    if date_match:
                        result["pickup_datetime"] = date_match.group(0).strip()
                        break

    if "delivery_datetime" not in result:
        for i, line in enumerate(lines):
            if re.search(r'deliver|destination|drop[\s-]*off', line, re.IGNORECASE):
                date_match = re.search(date_formats, line)
                if date_match:
                    result["delivery_datetime"] = date_match.group(0).strip()
                    break
                if i + 1 < len(lines):
                    date_match = re.search(date_formats, lines[i + 1])
                    if date_match:
                        result["delivery_datetime"] = date_match.group(0).strip()
                        break

    # ── Equipment Type ──
    equip_patterns = [
        r'equipment\s*(?:type)?\s*:\s*(.+?)(?:\n|$)',
        r'trailer\s*(?:type|size)?\s*:\s*(.+?)(?:\n|$)',
        r'truck\s*(?:type)?\s*:\s*(.+?)(?:\n|$)',
    ]
    val = _find_value_after_label(text, equip_patterns)
    if val and not _is_junk_value(val):
        result["equipment_type"] = val[:50]
    else:
        equip_kws = [
            ("53' dry van", "53' Dry Van"), ("48' dry van", "48' Dry Van"),
            ("53' reefer", "53' Reefer"), ("48' reefer", "48' Reefer"),
            ("53ft", "53' Trailer"), ("48ft", "48' Trailer"),
            ("dry van", "Dry Van"), ("reefer", "Reefer"),
            ("flatbed", "Flatbed"), ("step deck", "Step Deck"),
            ("tanker", "Tanker"), ("container", "Container"),
            ("box truck", "Box Truck"), ("sprinter", "Sprinter Van"),
        ]
        for kw, display in equip_kws:
            if kw in text_lower:
                result["equipment_type"] = display
                break

    # ── Mode ──
    mode_patterns = [
        r'mode\s*:\s*(.+?)(?:\n|$)',
        r'transportation\s*mode\s*:\s*(.+?)(?:\n|$)',
        r'service\s*(?:type|mode)\s*:\s*(.+?)(?:\n|$)',
        r'load\s*type\s*:?\s*\n?\s*(FTL|LTL|INTERMODAL)',
    ]
    val = _find_value_after_label(text, mode_patterns)
    if val and not _is_junk_value(val):
        result["mode"] = val.strip()
    else:
        mode_kws = [
            ("FULL TRUCKLOAD", "FTL"), ("FTL", "FTL"),
            ("LESS THAN TRUCKLOAD", "LTL"), ("LESS-THAN-TRUCKLOAD", "LTL"), ("LTL", "LTL"),
            ("INTERMODAL", "Intermodal"), ("DRAYAGE", "Drayage"),
            ("AIR FREIGHT", "Air Freight"), ("OCEAN", "Ocean"),
            ("PARTIAL", "Partial"),
        ]
        for kw, mode_val in mode_kws:
            if kw in text_upper:
                result["mode"] = mode_val
                break

    # ── Rate ──
    rate_patterns = [
        r'(?:carrier\s*pay\s*)?total\s*[:=]?\s*\$?\s*([\d,]+\.?\d{0,2})\s*USD',
        r'total\s*(?:rate|charges?|due|amount|cost)\s*[:=]?\s*\$?\s*([\d,]+\.?\d{0,2})',
        r'(?:agreed|contracted|all[\s-]*in)\s*(?:rate|amount|price)\s*[:=]?\s*\$?\s*([\d,]+\.?\d{0,2})',
        r'TOTAL\s*(?:DUE)?\s*[:=]?\s*\$?\s*([\d,]+\.?\d{0,2})',
        r'line\s*haul\s*(?:rate)?\s*[:=]?\s*\$?\s*([\d,]+\.?\d{0,2})',
        r'(?:freight\s+)?rate\s*[:=]?\s*\$?\s*([\d,]+\.?\d{0,2})',
        r'amount\s*[:=]?\s*\$\s*([\d,]+\.?\d{0,2})',
        r'(?:agreed\s+)?amount\s*\(USD\)\s*.*?\$?\s*([\d,]+\.?\d{0,2})',
    ]
    for pattern in rate_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            rate_val = match.group(1).replace(",", "").strip()
            try:
                rate_num = float(rate_val)
                if 10 < rate_num < 1000000:
                    result["rate"] = rate_val
                    break
            except ValueError:
                continue

    # Standalone dollar amounts fallback
    if "rate" not in result:
        dollar_matches = re.findall(r'\$\s*([\d,]+\.\d{2})', text)
        if dollar_matches:
            amounts = []
            for m in dollar_matches:
                try:
                    v = float(m.replace(",", ""))
                    if 10 < v < 1000000:
                        amounts.append(v)
                except ValueError:
                    pass
            if amounts:
                result["rate"] = f"{max(amounts):.2f}"

    # ── Currency ──
    if "$" in text or "USD" in text_upper:
        result["currency"] = "USD"
    elif "CAD" in text_upper:
        result["currency"] = "CAD"
    elif "EUR" in text_upper or "€" in text:
        result["currency"] = "EUR"
    elif "GBP" in text_upper or "£" in text:
        result["currency"] = "GBP"

    # ── Weight ──
    weight_patterns = [
        r'(?:gross\s+)?weight\s*:?\s*([\d,]+\.?\d*)\s*(lbs?|kg|tons?|pounds?)',
        r'(?:total\s+)?weight\s*:?\s*([\d,]+\.?\d*)\s*(lbs?|kg|tons?|pounds?)',
        r'([\d,]+\.?\d+)\s*(lbs?|pounds?)',                    # decimal weight like 56000.00 lbs
        r'([\d,]{3,})\s*(lbs?|pounds?)',                        # integer weight like 42,500 lbs
    ]
    for pattern in weight_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            weight_num = match.group(1).strip()
            weight_unit = match.group(2).strip() if match.lastindex >= 2 else "lbs"
            try:
                wn = float(weight_num.replace(",", ""))
                if wn >= 50:
                    result["weight"] = f"{weight_num} {weight_unit}".strip()
                    break
            except ValueError:
                continue

    # ── Carrier Name ──
    def _parse_carrier_from_row(raw_line: str) -> Optional[str]:
        """Parse carrier company name from a table data row."""
        if not raw_line or _is_junk_value(raw_line):
            return None
        # Extract everything before MC number, phone, or dollar sign
        company_match = re.match(
            r'^(.+?)\s+(?:MC[\-\s]?\d|\(\d{3}\)|\$\d)',
            raw_line
        )
        if company_match:
            name = company_match.group(1).strip()
            if name and len(name) > 2 and not _is_junk_value(name):
                return name
        # Try first segment with double-space split
        parts = re.split(r'\s{2,}', raw_line)
        if parts and len(parts[0].strip()) > 2 and not _is_junk_value(parts[0].strip()):
            return parts[0].strip()
        # If it's a short, clean line (< 8 words), use as-is
        if len(raw_line.split()) <= 6 and not _is_junk_value(raw_line):
            return raw_line
        return None

    carrier_patterns = [
        r'carrier\s*name\s*:\s*(.+?)(?:\n|$)',
        r'trucking\s*(?:company|co\.?)\s*:\s*(.+?)(?:\n|$)',
        r'transport(?:ation)?\s*(?:company|provider)\s*:\s*(.+?)(?:\n|$)',
    ]
    val = _find_value_after_label(text, carrier_patterns)
    if val and not _is_junk_value(val) and len(val.split()) <= 8:
        result["carrier_name"] = val[:100]
        val = None  # Already assigned, skip further logic
    else:
        val = None

    if "carrier_name" not in result:
        # Try "Carrier Details" or "Carrier Information" header approach
        for i, line in enumerate(lines):
            stripped = line.strip()
            if re.match(r'^carrier\s*(?:information|details)\s*$', stripped, re.IGNORECASE):
                # Skip column headers (junk), find the data row
                for j in range(i + 1, min(i + 5, len(lines))):
                    candidate = lines[j].strip()
                    if not candidate:
                        continue
                    if _is_junk_value(candidate):
                        continue
                    # Try to parse carrier name from table data row
                    parsed = _parse_carrier_from_row(candidate)
                    if parsed:
                        result["carrier_name"] = parsed[:100]
                    break
                break

    if "carrier_name" not in result:
        # Last resort: look for "Transportation Company" in BOL format
        for i, line in enumerate(lines):
            if re.search(r'transportation\s+company', line, re.IGNORECASE):
                if i + 1 < len(lines):
                    candidate = lines[i + 1].strip()
                    if candidate and candidate != "-" and not _is_junk_value(candidate):
                        result["carrier_name"] = candidate[:100]
                break

    # Note which fields were found vs missing
    all_fields = [
        "shipment_id", "shipper", "consignee", "pickup_datetime",
        "delivery_datetime", "equipment_type", "mode", "rate",
        "currency", "weight", "carrier_name",
    ]
    found = [f for f in all_fields if f in result and result[f]]
    missing = [f for f in all_fields if f not in result or not result[f]]

    notes.append(f"Extraction method: regex-based (LLM unavailable)")
    notes.append(f"Fields found: {len(found)}/{len(all_fields)}")
    if missing:
        notes.append(f"Missing fields: {', '.join(missing)}")

    return result, notes


# ── LLM-based Extraction ───────────────────────────────────────────

def extract_structured_data(doc_id: str, model: str = "gpt-3.5-turbo") -> ExtractResponse:
    """
    Extract structured shipment data from a document.
    Uses LLM when available, falls back to regex-based extraction.
    """
    raw_text = get_raw_text(doc_id)

    # Truncate if too long (LLM context window limits)
    max_chars = 12000
    truncated = raw_text[:max_chars] if len(raw_text) > max_chars else raw_text

    client = get_openai_client()

    if client:
        try:
            return _extract_with_llm(client, doc_id, truncated, model)
        except Exception as e:
            print(f"[Extractor] LLM extraction failed: {e}, falling back to regex")

    # Fallback to regex
    return _extract_with_regex_pipeline(doc_id, raw_text)


def _extract_with_llm(client: OpenAI, doc_id: str, text: str, model: str) -> ExtractResponse:
    """Extract using LLM."""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": EXTRACTION_PROMPT},
            {"role": "user", "content": f"Extract structured data from this logistics document:\n\n{text}"},
        ],
        temperature=0.0,
        max_tokens=800,
    )

    content = response.choices[0].message.content.strip()

    # Try to parse JSON from response
    try:
        # Handle markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        data = json.loads(content)
    except json.JSONDecodeError:
        # Try to find JSON in the response
        json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
        else:
            raise ValueError(f"Could not parse JSON from LLM response: {content[:200]}")

    # Build ShipmentData
    shipment = ShipmentData(
        shipment_id=data.get("shipment_id"),
        shipper=data.get("shipper"),
        consignee=data.get("consignee"),
        pickup_datetime=data.get("pickup_datetime"),
        delivery_datetime=data.get("delivery_datetime"),
        equipment_type=data.get("equipment_type"),
        mode=data.get("mode"),
        rate=str(data.get("rate")) if data.get("rate") else None,
        currency=data.get("currency"),
        weight=str(data.get("weight")) if data.get("weight") else None,
        carrier_name=data.get("carrier_name"),
    )

    # Count extracted fields for confidence
    fields = shipment.model_dump()
    found = sum(1 for v in fields.values() if v is not None)
    total = len(fields)

    notes = [
        "Extraction method: LLM-based (OpenAI)",
        f"Fields extracted: {found}/{total}",
    ]
    missing = [k for k, v in fields.items() if v is None]
    if missing:
        notes.append(f"Missing fields: {', '.join(missing)}")

    confidence = found / total

    return ExtractResponse(
        document_id=doc_id,
        shipment_data=shipment,
        confidence_score=round(confidence, 4),
        extraction_notes=notes,
    )


def _extract_with_regex_pipeline(doc_id: str, text: str) -> ExtractResponse:
    """Full regex extraction pipeline."""
    extracted, notes = _extract_with_regex(text)

    shipment = ShipmentData(
        shipment_id=extracted.get("shipment_id"),
        shipper=extracted.get("shipper"),
        consignee=extracted.get("consignee"),
        pickup_datetime=extracted.get("pickup_datetime"),
        delivery_datetime=extracted.get("delivery_datetime"),
        equipment_type=extracted.get("equipment_type"),
        mode=extracted.get("mode"),
        rate=extracted.get("rate"),
        currency=extracted.get("currency"),
        weight=extracted.get("weight"),
        carrier_name=extracted.get("carrier_name"),
    )

    fields = shipment.model_dump()
    found = sum(1 for v in fields.values() if v is not None)
    total = len(fields)
    confidence = found / total

    return ExtractResponse(
        document_id=doc_id,
        shipment_data=shipment,
        confidence_score=round(confidence, 4),
        extraction_notes=notes,
    )
