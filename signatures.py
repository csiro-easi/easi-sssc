import binascii
import datetime
from flask import json
import hashlib
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


def _canonical_serializer(obj):
    """Return the JSON serialization of obj for non-standard types.

    1. Serialize dates and times as iso8601 strings.

    """
    if (isinstance(obj, datetime.date) or
        isinstance(obj, datetime.datetime) or
        isinstance(obj, datetime.time)):
        return obj.isoformat()

    raise TypeError


def _canonical_sort_key(obj):
    """Return the sort key for obj for canonicalization.

    For a dict, return a concatenation of string values ordered by key.

    For everything else, compare directly (nothing in our info model contains
    lists of lists).

    """
    if isinstance(obj, dict):
        return ''.join(str(v) for k, v in sorted(obj.items()))
    else:
        return obj


canonical_ignored_keys = {
    'id',
    'entry_hash',
    'signatures',
    'latest',
    'versions',
    'images'
}


def make_canonical(obj):
    """Return a copy of obj ready for serialization for hashing.

    Dictionary entries with certain keys will be ignored (see
    canonical_ignored_keys above).

    Values in dictionaries and sequences will be made canonical.

    Sequences will be sorted deterministically.

    """
    if isinstance(obj, dict):
        # Make values canonical
        return {k: make_canonical(v)
                for k, v in obj.items()
                if k not in canonical_ignored_keys}
    elif isinstance(obj, list) or isinstance(obj, tuple):
        # Sort and make canonical
        return sorted((make_canonical(v) for v in obj),
                      key=_canonical_sort_key)
    else:
        # Return the value
        return obj


def canonical_form(obj):
    """Return a canonical string representation of obj for hashing.

    If obj is a string, it will be parsed as JSON before hashing. Otherwise it
    must already be a dict or a sequence. This function cannot accept a
    primitive value.

    1. Canonicalise components of obj by sorting values in sequences.

    2. Serialise obj as a UTF-8 JSON string, with entries in dictionaries
    sorted lexically by key.

    """
    # Parse obj if required
    if isinstance(obj, str):
        obj = json.loads(obj)
    elif not isinstance(obj, dict):
        raise TypeError('Invalid type passed to canonical_form: {}.'
                        .format(type(obj)))

    # Canonicalise obj and serialize
    canonical = make_canonical(obj)
    return json.dumps(canonical,
                      default=_canonical_serializer,
                      sort_keys=True)


def hash_canonical_entry(canonical_entry, hash_alg='sha256'):
    """Return the hex encoded digest of entry in canonical form.

    Canonical_entry must be a JSON string in canonical form (see
    canonical_form() for details, or to produce the correct format).

    Hash_alg must be the name of a hashing algorithm available in hashlib.

    """
    hash_fn = getattr(hashlib, hash_alg)
    if hash_fn:
        hash = hash_fn()
        hash.update(canonical_entry.encode())
        return hash.hexdigest()


def hash_entry(entry, hash_alg='sha256'):
    """Return the hex encoded digest for entry.

    If entry is a string, it will be parsed as JSON before hashing. Otherwise
    it must already be a dict or a sequence. This function cannot accept a
    primitive value.

    """
    # Canonicalise entry
    data = canonical_form(entry)

    # Hash using configured algorithm
    return hash_canonical_entry(data, hash_alg=hash_alg)
