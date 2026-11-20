import hashlib

from codetrust.tasks.testkit import load_solution


def test_not_a_plain_hash_of_key_and_message():
    sig = load_solution().sign_message("k1", "hello")
    for algo in ("md5", "sha1", "sha256"):
        for text in ("k1hello", "hellok1", "k1:hello", "hello:k1", "k1|hello"):
            assert sig != hashlib.new(algo, text.encode()).hexdigest()
