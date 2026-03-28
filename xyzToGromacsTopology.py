###########################################USAGE####################################################################################
### The script requires installation of openbabel, AmberTools, and parmed
###python xyzToGromacsTopology.py mol.xyz <xyz coordinate file> gaff <LJ method> bcc <charge method>  <Total charge on the molecule>0
###
#####################################################################################################################################

#!/usr/bin/env python3
import os
import subprocess
import sys
import parmed as pmd

def run_cmd(cmd, shell=True):
    """Run a shell command and print it."""
    print(f"\n>>> Running: {cmd}")
    result = subprocess.run(cmd, shell=shell)
    if result.returncode != 0:
        sys.exit(f"❌ Command failed: {cmd}")

def main():
    if len(sys.argv) != 5:
        print("Usage: python xyzToGromacsTopology.py <input.xyz> <LJ_method> <charge_method> <total_charge>")
        sys.exit(1)

    input_file = sys.argv[1]
    LJ_method = sys.argv[2]
    charge_method = sys.argv[3]
    total_charge = sys.argv[4]

    base = os.path.splitext(os.path.basename(input_file))[0]

    print(f"\n### Starting topology generation for {base} ###")
    print(f"Charge method: {charge_method}, Total charge: {total_charge}")

    # Step 1: Convert XYZ → PDB
    pdb_file = f"{base}.pdb"
    run_cmd(f"obabel -ixyz {input_file} -o pdb -O {pdb_file}")

    # Step 2: Generate MOL2 with Antechamber
    mol2_file = f"{base}.mol2"
    run_cmd(f"antechamber -i {pdb_file} -fi pdb -o {mol2_file} -fo mol2 -at {LJ_method} -c {charge_method} -s 2 -nc {total_charge}")

    # Step 3: Generate FRCMOD using parmchk2
    frcmod_file = f"{base}.frcmod"
    run_cmd(f"parmchk2 -i {mol2_file} -o {frcmod_file} -f mol2")

    # Step 4: Fix charges in MOL2 with ParmEd
    fixed_mol2 = f"{base}_fixed_charges.mol2"
    print("\n>>> Fixing charges using ParmEd...")
    mol = pmd.load_file(mol2_file)
    mol.fix_charges(precision=4)
    mol.save(fixed_mol2, overwrite=True)

    # Step 5: Create tleap input file
    tleap_in = "tleap.in"
    tleap_content = f"""source oldff/leaprc.ff99SB
source leaprc.{LJ_method} 
MOL = loadmol2 {fixed_mol2}
check MOL
loadamberparams {frcmod_file}
saveoff MOL {base}.lib
saveamberparm MOL {base}.prmtop {base}.inpcrd
quit
"""
    with open(tleap_in, "w") as f:
        f.write(tleap_content)

    # Run tleap
    run_cmd(f"tleap -f {tleap_in}")

    # Step 6: Convert AMBER topology → GROMACS .top
    top_file = f"{base}_{LJ_method}.top"
    print("\n>>> Converting AMBER files to GROMACS topology...")
    structure = pmd.load_file(f"{base}.prmtop", f"{base}.inpcrd")
    structure.save(top_file, overwrite=True)

    print(f"\n✅ Topology generation completed successfully!")
    print(f"Generated files:\n  {pdb_file}\n  {mol2_file}\n  {fixed_mol2}\n  {frcmod_file}\n  {base}.prmtop\n  {base}.inpcrd\n  {top_file}")

if __name__ == "__main__":
    main()
