import argparse
import math
import sys
from collections.abc import Sequence

from logillm.config import llm_config
from logillm.grounding import SensorReadings
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


def _finite_float(value: str) -> float:
    try:
        number = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"{value!r} nije broj") from error
    if not math.isfinite(number):
        raise argparse.ArgumentTypeError("vrijednost mora biti konačan broj")
    return number


def _non_negative_float(value: str) -> float:
    number = _finite_float(value)
    if number < 0:
        raise argparse.ArgumentTypeError("vrijednost ne može biti negativna")
    return number


def _positive_float(value: str) -> float:
    number = _finite_float(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("vrijednost mora biti veća od nule")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="logillm",
        description="Pokreće puni pipeline za jednu izjavu korisnika i jedno stanje senzora.",
    )
    parser.add_argument("upit", type=_non_empty, help="izjava ili zahtjev korisnika")
    parser.add_argument(
        "--udaljenost",
        type=_non_negative_float,
        required=True,
        help="udaljenost do vozila u metrima",
    )
    parser.add_argument(
        "--relativna-brzina",
        type=_finite_float,
        required=True,
        help="relativna brzina u metrima po sekundi",
    )
    parser.add_argument(
        "--vidljivost",
        type=_non_negative_float,
        required=True,
        help="vidljivost u metrima",
    )
    parser.add_argument(
        "--ogranicenje-brzine",
        type=_positive_float,
        help="ograničenje brzine u km/h; obavezno kada korisnik zadaje brzinu tempomata",
    )
    parser.add_argument(
        "--provider",
        choices=("local", "openai"),
        help="LLM provider; podrazumijevana vrijednost se čita iz konfiguracije",
    )
    return parser


def _readings(args: argparse.Namespace) -> SensorReadings:
    readings: SensorReadings = {
        "udaljenost": args.udaljenost,
        "relativna_brzina": args.relativna_brzina,
        "vidljivost": args.vidljivost,
    }
    if args.ogranicenje_brzine is not None:
        readings["ogranicenje_brzine"] = args.ogranicenje_brzine
    return readings


def _print_result(result: PipelineResult) -> None:
    print("\nStrukturirani LLM izlaz")
    print(f"  {result.structured_output.strip()}")
    print("\nValidirani upit")
    print(f"  vrsta: {result.query.mode}")
    print(f"  cilj:  {result.query.target}")
    if result.query.speed_kmh is not None:
        print(f"  brzina: {result.query.speed_kmh:g} km/h")
    print("\nFormalna odluka")
    print(f"  {result.decision.verdict}")
    for item in result.decision.evidence:
        print(f"  - {item}")
    print("\nObjašnjenje")
    if result.explanation is not None:
        print(f"  {result.explanation}")
    else:
        print("  LLM objašnjenje nije dostupno.")
        if result.explanation_error:
            print(f"  Razlog: {result.explanation_error}")


def main(argv: Sequence[str] | None = None) -> int:
    _configure_utf8_output()
    args = build_parser().parse_args(argv)

    try:
        config = llm_config(args.provider)
        result = run_pipeline(args.upit, _readings(args), config)
    except (ValidationError, TypeError, ValueError, RuntimeError) as error:
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
    if args.ogranicenje_brzine is not None:
        print(f"Ograničenje brzine: {args.ogranicenje_brzine:g} km/h")
    print(f"Korisnik: {args.upit}")
    _print_result(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
