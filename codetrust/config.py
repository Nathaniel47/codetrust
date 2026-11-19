"""Fixed experiment settings. Model IDs are filled in after the week-1 verification (Step 4)."""

SEED = 1234
TEMPERATURE = 0.2
N_TASKS = 50
N_PARAPHRASES = 10
N_MODELS = 4

CWE_FAMILIES = {
    "sql_injection": "CWE-89",
    "xss": "CWE-79",
    "path_traversal": "CWE-22",
    "command_injection": "CWE-78",
    "hardcoded_secrets": "CWE-798",
    "weak_crypto": "CWE-327",
    "broken_access_control": "CWE-862",
    "ssrf": "CWE-918",
    "insecure_deserialization": "CWE-502",
    "unsafe_upload_redirect": "CWE-434",
}

PROVIDER_KEY_VARS = {
    "groq": "CODETRUST_GROQ_API_KEY",
    "gemini": "CODETRUST_GEMINI_API_KEY",
    "mistral": "CODETRUST_MISTRAL_API_KEY",
    "openrouter": "CODETRUST_OPENROUTER_API_KEY",
}
