import argparse
import sys
from collections.abc import Sequence

from logillm.config import llm_config
from logillm.facts import Facts
from logillm.llm.validate import ValidationError
from logillm.pipeline import PipelineResult, run_pipeline


def _configure_utf8_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def _non_empty(value: str) -> str:
    text = value.strip()
    if not text:
        raise argparse.ArgumentTypeError("upit ne smije biti prazan")
    return text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="logillm",
        description="Pokreće puni pipeline za jednu izjavu korisnika i jedno stanje senzora.",
    )
    parser.add_argument("upit", type=_non_empty, help="izjava ili zahtjev korisnika")
    parser.add_argument("--udaljenost", type=float, required=True, help="udaljenost do vozila u metrima")
    parser.add_argument(
        "--relativna-brzina",
        type=float,
        required=True,
        help="relativna brzina u metrima po sekundi",
    )
    parser.add_argument("--vidljivost", type=float, required=True, help="vidljivost u metrima")
    parser.add_argument(
        "--provider",
        choices=("local", "openai"),
        help="LLM provider; podrazumijevana vrijednost se čita iz konfiguracije",
    )
    return parser


def _facts(args: argparse.Namespace) -> Facts:
    return {
        "udaljenost": args.udaljenost,
        "relativna_brzina": args.relativna_brzina,
        "vidljivost": args.vidljivost,
    }


def _print_result(result: PipelineResult) -> None:
    print("\nLLM izlaz")
    print(f"  {result.translation.strip()}")
    print("\nValidirani upit")
    print(f"  vrsta: {result.query.mode}")
    print(f"  cilj:  {result.query.target}")
    print("\nFormalna odluka")
    print(f"  {result.decision.verdict}")
    for item in result.decision.evidence:
        print(f"  - {item}")
    print("\nObjašnjenje")
    print(f"  {result.explanation}")


def main(argv: Sequence[str] | None = None) -> int:
    _configure_utf8_output()
    args = build_parser().parse_args(argv)

    try:
        config = llm_config(args.provider)
        result = run_pipeline(args.upit, _facts(args), config)
    except (ValidationError, ValueError, RuntimeError) as error:
        print(f"Greška: {error}", file=sys.stderr)
        return 1

    print(f"Provider: {config.provider}")
    print(f"Model:    {config.model}")
    print(
        "Senzori:  "
        f"udaljenost={args.udaljenost}, "
        f"relativna_brzina={args.relativna_brzina}, "
        f"vidljivost={args.vidljivost}"
    )
    print(f"Korisnik: {args.upit}")
    _print_result(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
