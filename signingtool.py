import argparse
import json
from views import hash_str, hash_dict


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
                        help="URL pointing to the entry that us to be signed", required=True)
    parser.add_argument('-s', '--signatureurl', action='store',
                        help="URL poiting to the destination where the signature will be submitted to", required=True)

    args = parser.parse_args()

    with open(args.filename, "r") as entry_file:
        entry_str = entry_file.read()
        entry_dict = json.loads(entry_str)
        entry_hash = hash_dict(entry_dict, log_file="C:\\opt\\sign_entry.json")
        print(entry_hash)

