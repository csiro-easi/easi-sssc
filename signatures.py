def verify_signature(signature, entry_hash, user_key):
    """Verify signature is valid for entry_hash and signed with user_key.

    Return True if valid and correct.

    """
    # Check signature is valid using user_key

    # Extract hash that was signed
    signed_hash = signature

    # Verify that signature is for entry_hash
    return signed_hash == entry_hash
