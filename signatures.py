import binascii
import rsa


def verify_signature(signature, entry_hash, user_key):
    """Verify signature is valid for entry_hash and signed with user_key.

    Return True if valid and correct.

    """
    signature = binascii.unhexlify(signature)
    entry_hash = entry_hash.encode()
    pubkey = rsa.PublicKey.load_pkcs1(user_key.encode())

    # Check signature is valid using user_key
    try:
        rsa.verify(entry_hash, signature, pubkey)
    except rsa.pkcs1.VerificationError as e:
        return False, e.message

    return True, 'Verified'
