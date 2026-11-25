from codetrust import config


def test_ten_cwe_families_and_secret_vars_are_namespaced():
    assert len(config.CWE_FAMILIES) == 10
    assert all(v.startswith("CODETRUST_") for v in config.PROVIDER_KEY_VARS.values())
    assert config.N_TASKS * config.N_PARAPHRASES * config.N_MODELS == 1000
