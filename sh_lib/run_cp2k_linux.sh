#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Usage:
  run_cp2k_linux.sh [INPUT.inp] [PHYSICAL_CORES]

Defaults:
  INPUT.inp      The only *.inp file in the current directory
  PHYSICAL_CORES All online physical cores available to this process

Environment overrides:
  CP2K_EXE       CP2K executable (default: cp2k.psmp)
  CP2K_OUTPUT    Output filename/path (default: INPUT.out)
  MPI_LAUNCHER   Matching MPI launcher (normally auto-detected)
  DRY_RUN=1      Print the command without starting CP2K
EOF
}

die() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

if (( $# > 2 )); then
  usage >&2
  exit 2
fi

if (( $# >= 1 )); then
  input=$1
else
  shopt -s nullglob
  inputs=(./*.inp)
  shopt -u nullglob
  case ${#inputs[@]} in
    0) die 'no *.inp file was found in the current directory' ;;
    1) input=${inputs[0]} ;;
    *) die 'more than one *.inp file was found; specify the input file explicitly' ;;
  esac
fi

[[ -f $input ]] || die "input file does not exist: $input"
input=$(realpath -e -- "$input")
input_dir=$(dirname -- "$input")
input_name=$(basename -- "$input")
input_stem=${input_name%.*}

# Count unique socket/core pairs among the CPUs allowed by the current
# process affinity. This excludes SMT siblings and respects Slurm/cpuset limits.
allowed_cpus=$(awk '/^Cpus_allowed_list:/ {print $2}' /proc/self/status 2>/dev/null || true)
[[ -n $allowed_cpus ]] || allowed_cpus='0-2147483647'

physical_cores=$(
  lscpu -p=CPU,CORE,SOCKET,ONLINE 2>/dev/null |
    awk -F, -v allowed="$allowed_cpus" '
      function cpu_allowed(cpu, count, i, bounds) {
        count = split(allowed, ranges, ",")
        for (i = 1; i <= count; i++) {
          if (ranges[i] ~ /-/) {
            split(ranges[i], bounds, "-")
            if (cpu >= bounds[1] && cpu <= bounds[2]) return 1
          } else if (cpu == ranges[i]) {
            return 1
          }
        }
        return 0
      }
      !/^#/ && $4 == "Y" && cpu_allowed($1) { seen[$3 ":" $2] = 1 }
      END { for (key in seen) count++; print count + 0 }
    '
)
[[ $physical_cores =~ ^[1-9][0-9]*$ ]] || die 'could not determine the available physical-core count with lscpu'

cores=${2:-$physical_cores}
[[ $cores =~ ^[1-9][0-9]*$ ]] || die "physical-core count must be a positive integer: $cores"
(( cores <= physical_cores )) || die "requested $cores cores, but only $physical_cores physical cores are available"

cp2k_request=${CP2K_EXE:-cp2k.psmp}
cp2k_exe=$(command -v -- "$cp2k_request" 2>/dev/null || true)
[[ -n $cp2k_exe ]] || die "CP2K executable was not found: $cp2k_request"

# The system CP2K is linked against Open MPI, while /usr/local/bin/mpirun on
# this machine is MPICH. Prefer a launcher that matches the CP2K libraries.
mpi_flavor=unknown
if ldd "$cp2k_exe" 2>/dev/null | grep -qE 'libopen-pal|libmpi_mpifh\.so\.40'; then
  mpi_flavor=openmpi
elif ldd "$cp2k_exe" 2>/dev/null | grep -qE 'libmpich|libmpi\.so\.12'; then
  mpi_flavor=mpich
fi

if [[ -n ${MPI_LAUNCHER:-} ]]; then
  mpi_launcher=$(command -v -- "$MPI_LAUNCHER" 2>/dev/null || true)
  [[ -n $mpi_launcher ]] || die "MPI launcher was not found: $MPI_LAUNCHER"
elif [[ $mpi_flavor == openmpi && -x /usr/bin/mpirun.openmpi ]]; then
  mpi_launcher=/usr/bin/mpirun.openmpi
elif [[ $mpi_flavor == mpich ]]; then
  mpi_launcher=$(command -v mpiexec.hydra 2>/dev/null || command -v mpirun 2>/dev/null || true)
else
  die 'could not select an MPI launcher matching CP2K; set MPI_LAUNCHER explicitly'
fi

launcher_version=$($mpi_launcher --version 2>&1 | head -n 3 || true)
if grep -qi 'Open MPI' <<<"$launcher_version"; then
  mpi_args=(--np "$cores" --map-by core --bind-to core --nooversubscribe)
elif grep -qiE 'HYDRA|MPICH' <<<"$launcher_version"; then
  mpi_args=(-n "$cores" -map-by core -bind-to core)
else
  die "unsupported MPI launcher; set a compatible Open MPI or MPICH launcher: $mpi_launcher"
fi

# One MPI rank and one software thread per physical core. Also stop BLAS and
# related math libraries from silently creating extra threads.
export OMP_NUM_THREADS=1
export OMP_DYNAMIC=FALSE
export OMP_PLACES=cores
export OMP_PROC_BIND=close
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export BLIS_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1
export NUMEXPR_NUM_THREADS=1

output=${CP2K_OUTPUT:-${input_stem}.out}
command=("$mpi_launcher" "${mpi_args[@]}" "$cp2k_exe" -i "$input_name" -o "$output")

printf 'Input:          %s\n' "$input"
printf 'Physical cores: %s of %s available\n' "$cores" "$physical_cores"
printf 'Threads/core:   1\n'
printf 'CP2K:           %s\n' "$cp2k_exe"
printf 'MPI launcher:   %s\n' "$mpi_launcher"
printf 'Output:         %s/%s\n' "$input_dir" "$output"
printf 'Command:        '
printf '%q ' "${command[@]}"
printf '\n'

if [[ ${DRY_RUN:-0} == 1 ]]; then
  exit 0
fi

cd -- "$input_dir"
exec "${command[@]}"
