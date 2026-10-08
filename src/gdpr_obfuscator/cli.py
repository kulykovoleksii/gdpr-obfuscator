import argparse
import os
import logging
from .format_adapters import detect_format_from_filename
from .obfuscator import obfuscate_stream


def main(argv=None):
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger = logging.getLogger(__name__)

    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--fields", required=True)  # comma separated
    p.add_argument("--pk", default="id")
    p.add_argument(
        "--mask", action="store_true", help="Use fixed mask instead of tokens"
    )
    p.add_argument(
        "--mask-token", default="***", help="Custom mask string (default: ***)"
    )
    p.add_argument(
        "--format",
        choices=["csv", "json", "jsonl", "parquet"],
        help="File format (default: detect from input file extension)",
    )
    p.add_argument(
        "--token-length",
        type=int,
        default=16,
        help="Length of hex tokens in token mode (default: 16)",
    )

    args = p.parse_args(argv)
    key = os.getenv("OBFUSCATOR_KEY")

    if not key:
        logger.error("Missing OBFUSCATOR_KEY environment variable")
        raise SystemExit("Missing OBFUSCATOR_KEY")

    sensitive = [f.strip() for f in args.fields.split(",")]
    logger.info(
        "Run CLI: input=%s output=%s fields=%s pk=%s",
        args.input,
        args.output,
        sensitive,
        args.pk,
    )

    mode = "mask" if args.mask else "token"
    file_format = args.format or detect_format_from_filename(args.input)

    with open(args.input, "rb") as fin, open(args.output, "wb") as fout:
        obfuscate_stream(
            fin,
            fout,
            sensitive,
            file_format=file_format,
            primary_key_field=args.pk,
            key=key.encode("utf-8"),
            mode=mode,
            mask_token=args.mask_token,
            token_length=args.token_length,
        )


if __name__ == "__main__":
    main()
