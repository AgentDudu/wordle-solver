"""The command-line entry point: play today's puzzle, or print today's answer."""

import argparse
import re
import sys

from wordle import nytimes, play


def _five_letters(value: str) -> str:
    answer = value.lower()
    if not re.fullmatch(r"[a-z]{5}", answer):
        raise argparse.ArgumentTypeError(f"{value!r} is not five letters a-z")
    return answer


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python main.py",
        description=(
            "Suggest Wordle guesses that are guaranteed to land on the answer at attempt N. "
            "The answer is printed up front; you play the words, the tool reads the colours."
        ),
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=("play", "answer"),
        default="play",
        help="answer prints today's answer and exits (default: play)",
    )
    parser.add_argument(
        "-n",
        "--attempts",
        type=int,
        choices=(3, 4),
        help="the attempt the answer is guessed on; omit it and the run asks, Enter takes 4",
    )
    parser.add_argument(
        "-a",
        "--answer",
        type=_five_letters,
        metavar="WORD",
        help="use this answer instead of fetching today's from NYT",
    )
    args = parser.parse_args(argv)
    if args.command == "answer":
        return _print_answer(args.answer)
    return play.main(attempts=args.attempts, answer=args.answer)


def _print_answer(answer: str | None) -> int:
    day = nytimes.today()
    if answer:
        print(f"{day.isoformat()}  {answer}  (given on the command line)")
        return 0
    try:
        answer, source = nytimes.lookup(day)
    except Exception as exc:  # URLError, HTTPError, bad JSON, unusable solution
        print(f"could not get today's answer: {exc}")
        print("pass it directly: python main.py answer --answer <answer>")
        return 1
    print(f"{day.isoformat()}  {answer}  ({source})")
    return 0


if __name__ == "__main__":
    # typeshed types sys.stdout as TextIO, which has no reconfigure; at runtime it is a
    # TextIOWrapper and this is the documented way to get emoji onto a cp1252 Windows console.
    sys.stdout.reconfigure(encoding="utf-8")  # pyright: ignore[reportAttributeAccessIssue]  # type: ignore[attr-defined]
    raise SystemExit(main())
