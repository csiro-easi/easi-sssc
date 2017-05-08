import argparse
import json
from views import hash_dict
from rsa import PrivateKey
import rsa
from datetime import datetime

#
# Key Pair creation:
# Private key: openssl genrsa -out rsakey.pem 2048
# Public  key: openssl rsa -in rsakey.pem -pubout > rsakey.pub.pem
#

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

    entry_hash=None

    with open(args.filename, "r") as entry_file:
        entry_str = entry_file.read()
        entry_dict = json.loads(entry_str)
        entry_hash = hash_dict(entry_dict, log_file="C:\\opt\\sign_entry.json")
        print(entry_hash)

    private_key = None

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    signable_str = entry_hash+"$"+now

    with open(args.key, "r") as key_file:
        key_str = key_file.read()
        private_key = PrivateKey.load_pkcs1(key_str)

    signature  = rsa.sign(signable_str.encode("UTF-8"), private_key, "SHA-256")

    print("end")
