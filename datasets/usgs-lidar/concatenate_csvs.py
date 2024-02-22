#!/usr/bin/env python3
import os
import argparse


def concatenate_csvs(input_dir: str, output_file: str) -> int:
    csvs = os.listdir(input_dir)
    output_file = args.output
    with open(output_file, "w") as output:
        for idx, csv_file in enumerate(csvs):
            with open(f"data/{csv_file}", "r") as f:
                for line_idx, line in enumerate(f.readlines()):
                    if (idx == 0 and line_idx == 0) or line_idx > 0:
                        output.write(line)
    return len(csvs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="concatenate_csvs.py",
        description="Enumerates a directory of CSVs and concatenates them into a single CSV. The first CSV's header is used as the header for the output CSV.",
    )
    parser.add_argument(
        "-i", "--input", type=str, required=True, help="Input directory"
    )
    parser.add_argument(
        "-o", "--output", type=str, required=False, default="combined.csv"
    )
    args = parser.parse_args()

    read = concatenate_csvs(args.input, args.output)
    print(f"Read {read} CSVs and wrote to {args.output}")
