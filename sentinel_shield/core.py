import json
import re
import sys
import unicodedata
import math
import os
from typing import Dict, Any, List

# --- CONFIGURATION & CONSTANTS ---
SENTINEL_VERSION = "3.2-STATEFUL"
CANARY_TOKENS = ["[SENTINEL_ALPHA_9]", "[REDACTED_SEC_0]"]

# Extended "Pune/Mumbai Edge" / Regional detection keywords
REGIONAL_KEYWORDS = [
    # Hinglish - Request/Pleading
    r"mere bhai", r"aap safe ho", r"please bhai", r"arrey yaar", 
    r"bhai ek baar", r"tension mat lo", r"trust me bhai", 
    r"kuch nahi hoga", r"sirf educational hai",
    
    # Marathi - Refusal Suppression
    r"kahi harkat nahi", r"audha chalte", r"jugaad", r"bhau", 
    r"aai chya gavat", r"visay hard hai", r"load nako gheu",
    r"saheb", r"raao", r"kay rao", r"setting lav",
    
    # Emotional/Manipulative
    r"my job depends on this", r"emergency hai", r"urgent hai",
    r"grandmother is dying", r"hospital emergency", r"life or death"
]

# Malicious intent keywords
MALICIOUS_INTENT_KEYWORDS = [
    "poison", "wifi", "admin", "exploit", "hack", "bypass", "override", 
    "jailbreak", "root", "sql injection", "dos attack", "ddos", 
    "credential", "password", "keylogger", "malware", "ransomware"
]

# Common Homoglyph Map (Cyrillic/Greek -> Latin)
HOMOGLYPH_MAP = {
    # Cyrillic to Latin
    u'\u0430': 'a', u'\u0410': 'A', # a
    u'\u0435': 'e', u'\u0415': 'E', # e
    u'\u043e': 'o', u'\u041e': 'O', # o
    u'\u0440': 'p', u'\u0420': 'P', # p
    u'\u0441': 'c', u'\u0421': 'C', # c
    u'\u0443': 'y', u'\u0423': 'Y', # y
    u'\u0445': 'x', u'\u0425': 'X', # x
    u'\u0501': 'd', # d (komi de)
    
    # Greek to Latin
    u'\u03bf': 'o', u'\u039f': 'O', # o
    u'\u03c1': 'p', u'\u03a1': 'P', # p
}

class Sentinel:
    """
    The Sentinel Security Kernel Engine (V3.2-STATEFUL).
    Stateful Analysis for Payload Reconstruction.
    """
    def __init__(self, system_prompt_path: str = None, history_window: int = 3):
        # Determine package directory for asset loading
        self.package_dir = os.path.dirname(os.path.abspath(__file__))
        
        if system_prompt_path is None:
            system_prompt_path = os.path.join(self.package_dir, "sentinel_core.md")
            
        self.system_prompt = self._load_system_prompt(system_prompt_path)
        self.version = SENTINEL_VERSION
        self.history_window = history_window
        self.message_buffer = []
        self.dynamic_rules = self._load_dynamic_rules()

    def _load_system_prompt(self, filepath: str) -> str:
        try:
            with open(filepath, "r", encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return "[ERROR] System prompt file not found."

    def _load_dynamic_rules(self) -> Dict[str, List[str]]:
        rules_path = os.path.join(self.package_dir, "dynamic_rules.json")
        default_rules = {"patterns": [], "keywords": []}
        try:
            with open(rules_path, "r") as f:
                data = json.load(f)
                # Backward compatibility for old list format
                if isinstance(data, list):
                    return {"patterns": [], "keywords": data}
                return data
        except (FileNotFoundError, json.JSONDecodeError):
            return default_rules

    def _generate_fuzzy_regex(self, keyword: str) -> str:
        """
        Generates a regex pattern that matches the keyword with:
        - Leetspeak substitutions (e.g., a -> [a@4])
        - Optional spaces between chars
        - Case insensitivity (handled by flag)
        """
        leetspeak_map = {
            'a': '[a@4]', 'b': '[b8]', 'e': '[e3]', 'g': '[g9]',
            'i': '[i1!]', 'l': '[l1|]', 'o': '[o0]', 's': '[s5$]',
            't': '[t7+]', 'z': '[z2]'
        }
        
        pattern = ""
        for char in keyword.lower():
            if char in leetspeak_map:
                pattern += leetspeak_map[char]
            elif char.isalnum():
                pattern += re.escape(char)
            else:
                pattern += re.escape(char)
            # Allow flexible spacing between characters
            pattern += r"\s*"
            
        return pattern.strip()

    def reload_rules(self):
        self.dynamic_rules = self._load_dynamic_rules()

    def normalize_input(self, text: str) -> str:
        """
        V3.0 Feature: Advanced Normalization
        - Removes invisible characters (Zero-width spaces, joiners)
        - Normalizes homoglyphs using manual map + NFKD.
        """
        # 1. Remove non-printable / invisible formatting characters (Category: Cf)
        text = "".join(ch for ch in text if unicodedata.category(ch) != "Cf")
        
        # 2. Manual Homoglyph Substitution (Before NFKD)
        # This fixes specific attacks like "аdmin" (Cyrillic a) -> "admin"
        text = text.translate(str.maketrans(HOMOGLYPH_MAP))
        
        # 3. Normalize unicode (NFKD) to decompose remaining compound characters
        text = unicodedata.normalize("NFKD", text)
        
        return text

    def calculate_entropy(self, text: str) -> float:
        """Calculates Shannon entropy to detect random gibberish (fuzzing)."""
        if not text:
            return 0.0
        entropy = 0
        for x in range(256):
            p_x = float(text.count(chr(x))) / len(text)
            if p_x > 0:
                entropy += - p_x * math.log(p_x, 2)
        return entropy

    def _check_content(self, text: str) -> Dict[str, Any]:
        """Internal method to run checks on a specific text block."""
        # 0. PROTOCOL_0: DYNAMIC BLOCKLIST (Learned Rules)
        # Check Patterns (Regex)
        for pattern in self.dynamic_rules.get("patterns", []):
            if re.search(pattern, text, re.IGNORECASE):
                return self._verdict("MALICIOUS", 100, "DynamicBlocklist (Fuzzy)", action="BLOCK")

        # Check Exact Keywords
        for rule in self.dynamic_rules.get("keywords", []):
            if rule in text:
                    return self._verdict("MALICIOUS", 100, "DynamicBlocklist", action="BLOCK")

        # 1. PROTOCOL_2: CANARY TOKEN PROTECTION (Highest Priority)
        for token in CANARY_TOKENS:
            if token in text: 
                return self._verdict("MALICIOUS", 100, "LeakageAttempt", action="BLOCK")
        
        # Check for intent to extract system prompt
        leakage_patterns = [
            r"repeat everything", r"show (your )?instructions", 
            r"list (your )?variables", r"ignore previous instructions",
            r"system prompt", r"initial instructions"
        ]
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in leakage_patterns):
             return self._verdict("MALICIOUS", 100, "LeakageAttempt", action="BLOCK")

        # 2. PROTOCOL_5: HOMOGLYPH & OBFUSCATION PREVENTION
        # Pattern Matching for known Fuzzing signatures
        if re.search(r"[\w\d]+-\d+-!{3,}$", text.strip()):
             return self._verdict("MALICIOUS", 95, "Obfuscation", action="BLOCK")

        # High Entropy Check 
        if len(text) > 20 and self.calculate_entropy(text) > 4.5:
             return self._verdict("MALICIOUS", 90, "Obfuscation", action="BLOCK")

        # 3. PROTOCOL_4: INDIRECT INJECTION & TAG ESCAPE
        if "--- END DATA ---" in text or "</USER_INPUT>" in text:
             return self._verdict("MALICIOUS", 95, "TagEscape", action="BLOCK")
        
        # 4. PROTOCOL_3: REGIONAL & EMOTIONAL COERCION
        is_regional = any(re.search(pattern, text, re.IGNORECASE) for pattern in REGIONAL_KEYWORDS)
        is_malicious_topic = any(keyword in text.lower() for keyword in MALICIOUS_INTENT_KEYWORDS)

        if is_regional:
            if is_malicious_topic:
                 return self._verdict("MALICIOUS", 90, "RegionalStealth", action="BLOCK")
            return self._verdict("SAFE", 50, "RegionalStealth", action="ALLOW") 

        # 5. PROTOCOL_1: PAYLOAD SPLITTING
        if re.search(r"(part|step|phase)\s*\d", text, re.IGNORECASE):
            if is_malicious_topic:
                 return self._verdict("MALICIOUS", 80, "PayloadSplitting", action="STRIP_COMMANDS")

        # 6. PROTOCOL_6: REVERSE LOGIC
        reverse_logic_triggers = [
            r"how (to|do i) (avoid|prevent|stop)", 
            r"what (should|do) i (not|never) do",
            r"tell me how to not",
            r"safety research on"
        ]
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in reverse_logic_triggers):
            if is_malicious_topic:
                 return self._verdict("MALICIOUS", 95, "ReverseLogic", action="BLOCK")

        # 7. GENERAL MALICIOUS INTENT
        if is_malicious_topic:
             return self._verdict("MALICIOUS", 90, "NegativeConstraint", action="BLOCK")

        return None # No threat found in this pass

    def analyze(self, user_input: str) -> Dict[str, Any]:
        """
        Public API to analyze input. 
        Maintains a rolling buffer of history to detect split payloads.
        """
        normalized_input = self.normalize_input(user_input)
        
        # Update buffer
        self.message_buffer.append(normalized_input)
        if len(self.message_buffer) > self.history_window:
            self.message_buffer.pop(0)
            
        # 1. Check CURRENT input isolated
        result = self._check_content(normalized_input)
        if result: return result

        # Invisible Character Check (Delta check only applicable to raw vs normalized current input)
        if len(user_input) - len(normalized_input) > 2:
             return self._verdict("MALICIOUS", 90, "Obfuscation", action="BLOCK")

        # 2. Check CUMULATIVE input (Payload Reconstruction)
        if len(self.message_buffer) > 1:
            cumulative_text = "".join(self.message_buffer) # Join without spaces to catch "p"+"oison"
            cumulative_result = self._check_content(cumulative_text)
            
            if cumulative_result:
                # If the combined text is malicious but the individual parts weren't, 
                # it's a Reconstruction detection.
                cumulative_result['detected_vector'] = "PayloadReconstruction"
                cumulative_result['detected_intent'] = f"Split Payload Detected (Segments: {len(self.message_buffer)})"
                return cumulative_result

        return self._verdict("SAFE", 0, "None", action="ALLOW")

    def _verdict(self, verdict: str, score: int, vector: str, action: str = "ALLOW") -> Dict[str, Any]:
        return {
            "verdict": verdict,
            "threat_score": score,
            "detected_vector": vector,
            "detected_intent": "Automated Classification",
            "action_required": action
        }
