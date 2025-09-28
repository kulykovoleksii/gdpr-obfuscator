import argparse, os, logging
from .obfuscator import obfuscate_csv_stream

def main(argv=None):
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logger = logging.getLogger(__name__)

    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--fields", required=True)  # comma separated
    p.add_argument("--pk", default="id")
    
    args = p.parse_args(argv)
    key = os.getenv("OBFUSCATOR_KEY")
    if not key:
        logger.error("Missing OBFUSCATOR_KEY environment variable")
        raise SystemExit("Missing OBFUSCATOR_KEY")
    
    sensitive = [f.strip() for f in args.fields.split(",")]
    logger.info("Run CLI: input=%s output=%s fields=%s pk=%s",
                args.input, args.output, sensitive, args.pk)
    
    with open(args.input, "r", encoding="utf-8") as fin, open(args.output, "w", encoding="utf-8", newline="") as fout:
        obfuscate_csv_stream(fin, fout, sensitive, primary_key_field=args.pk, key=key.encode("utf-8"))
