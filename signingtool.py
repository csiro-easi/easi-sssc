import argparse
from datetime import datetime
from rsa import PrivateKey
import rsa
import requests
from signatures import canonical_form, hash_canonical_entry
import json
import base64

#
# Key Pair creation:
# Private key: openssl genrsa -out rsakey.pem 2048
# Public  key: openssl rsa -in rsakey.pem -RSAPublicKey_out > rsakey.pub.pem
#


def post_dict(dict, url, auth = None):
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    r = requests.post(url, data=json.dumps(dict), headers=headers, auth=auth)
    return r

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Sign a SSSC entry")
    parser.add_argument('-u', '--username', action='store',
                        help="SSSC user name", required=True)
    parser.add_argument('-p', '--passwd', action='store',
                        help="SSSC password", required=True)
    parser.add_argument('-f', '--filename', action='store',
                        help="Filename of file containing the entry that is to be signed", required=True)
    parser.add_argument('-k', '--key', action='store',
                        help="Filename of the file containing the private signature key", required=True)
    parser.add_argument('-e', '--sourceurl', action='store',
                        help="URL pointing to the entry that is to be signed", required=True)
    parser.add_argument('-s', '--signatureurl', action='store',
                        help="URL poiting to the destination where the signature will be submitted to", required=True)

    args = parser.parse_args()

    with open(args.filename, "r") as entry_file:
        entry_str = entry_file.read()
        canonical_entry = canonical_form(entry_str)
        with open("C:\\opt\\sign_entry.json", 'w') as log_file:
            log_file.write(canonical_entry)
        entry_hash = hash_canonical_entry(canonical_entry)
        print(entry_hash)

    private_key = None

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    signable_str = entry_hash+"$"+now

    with open(args.key, "r") as key_file:
        key_str = key_file.read()
        private_key = PrivateKey.load_pkcs1(key_str)

    signature  = rsa.sign(signable_str.encode("UTF-8"), private_key, "SHA-256")
    signature_str = base64.encodebytes(signature).decode('utf-8')
    print(signature_str)

    signature_payload = {'signed_string': signable_str, 'signature': signature_str, 'entry_id': args.sourceurl}

    sig_post_res = post_dict(signature_payload, args.signatureurl, auth=(args.username, args.passwd))
    print(sig_post_res)

    print("end")
