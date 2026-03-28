##########Script for Replacing Charges in a Gromacs topology###############
##It requies a gromacs topology file and orca charge file. The order of the 
## atoms in both the files should be the same. The expamle files are given
## in the example folder. 
###########################################################################
#!/usr/bin/env python3
import argparse
from pathlib import Path


def prompt_if_missing(value: str | None, prompt_text: str) -> str:
    if value:
        return value
    return input(prompt_text).strip()


def read_charges(coord_file: str) -> list[float]:
    charges = []
    with open(coord_file, "r") as f:
        for lineno, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            parts = stripped.split()
            try:
                charges.append(float(parts[-1]))
            except ValueError as e:
                raise ValueError(
                    f"Could not parse charge on line {lineno} of {coord_file!r}: {line.rstrip()}"
                ) from e
    return charges


def update_topology_charges(itp_file: str, charges: list[float]) -> list[str]:
    with open(itp_file, "r") as f:
        lines = f.readlines()

    inside_atoms = False
    charge_idx = 0
    new_lines = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("[ atoms ]"):
            inside_atoms = True
            new_lines.append(line)
            continue

        if inside_atoms:
            # End of [ atoms ] section when a new section starts
            if stripped.startswith("[") and not stripped.startswith("[ atoms ]"):
                inside_atoms = False
                new_lines.append(line)
                continue

            # Keep comments and blank lines unchanged
            if stripped == "" or stripped.startswith(";"):
                new_lines.append(line)
                continue

            # Preserve inline comments if present
            if ";" in line:
                data_part, comment_part = line.split(";", 1)
                comment_part = ";" + comment_part.rstrip("\n")
            else:
                data_part = line.rstrip("\n")
                comment_part = ""

            parts = data_part.split()

            # Expected GROMACS atoms line has at least 8 columns:
            # nr type resnr residue atom cgnr charge mass
            if len(parts) >= 8:
                if charge_idx >= len(charges):
                    raise ValueError(
                        f"Not enough charges: found {len(charges)} charges, "
                        f"but topology needs more atom entries in [ atoms ]."
                    )

                parts[6] = f"{charges[charge_idx]:.6f}"
                charge_idx += 1

                new_line = (
                    f"{parts[0]:>6} {parts[1]:>5} {parts[2]:>5} {parts[3]:>8} "
                    f"{parts[4]:>8} {parts[5]:>5} {parts[6]:>12} {parts[7]:>10}"
                )

                if comment_part:
                    new_line += f" {comment_part}"

                new_lines.append(new_line + "\n")
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    if charge_idx < len(charges):
        print(
            f"Warning: {len(charges) - charge_idx} charge(s) were not used "
            f"(charges file has more entries than the [ atoms ] section)."
        )

    return new_lines


def main():
    parser = argparse.ArgumentParser(
        description="Replace charges in a GROMACS topology [ atoms ] section using values from a charge file."
    )
    parser.add_argument(
        "-c", "--charges",
        help="Input charge file (last column must contain the charge values)"
    )
    parser.add_argument(
        "-t", "--topology",
        help="Input topology file (.itp or .top)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file name"
    )

    args = parser.parse_args()

    coord_file = prompt_if_missing(args.charges, "Charge file: ")
    itp_file = prompt_if_missing(args.topology, "Topology file (.itp/.top): ")

    default_output = str(Path(itp_file).with_name(Path(itp_file).stem + "_resp" + Path(itp_file).suffix))
    output_file = prompt_if_missing(
        args.output,
        f"Output file [{default_output}]: "
    ) or default_output

    charges = read_charges(coord_file)
    new_lines = update_topology_charges(itp_file, charges)

    with open(output_file, "w") as f:
        f.writelines(new_lines)

    print(f"Charges updated and saved to: {output_file}")


if __name__ == "__main__":
    main()
