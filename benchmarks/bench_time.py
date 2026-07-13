"""Wall-clock + peak-RSS measurement, native and docker-contained.

``/usr/bin/time -v`` is ABSENT on this host, so we read the same underlying
``getrusage`` field it reports (``Maximum resident set size``) via ``os.wait4``'s
``ru_maxrss`` (KB on Linux). For docker-contained arms we read the cgroup-v2
``memory.peak`` (bytes) of the container -- the peak RSS the contained helios
process reached -- and detect an OOM kill via exit code 137.

Everything here is pure stdlib and spawns real subprocesses (never threads), so it
is safe to call from the concurrency harness' forked workers too.
"""

from __future__ import annotations

import os
import time


class RunResult:
    __slots__ = ("wall_s", "peak_rss_kb", "exit_code", "oomed", "stdout", "stderr")

    def __init__(self, wall_s, peak_rss_kb, exit_code, oomed, stdout="", stderr=""):
        self.wall_s = wall_s
        self.peak_rss_kb = peak_rss_kb
        self.exit_code = exit_code
        self.oomed = oomed
        self.stdout = stdout
        self.stderr = stderr


def run_native(argv, env=None, cwd=None, capture=False) -> RunResult:
    """Run ``argv`` natively; return wall time + peak RSS (KB) via ``os.wait4``.

    ``ru_maxrss`` is the identical field ``/usr/bin/time -v`` prints as
    ``Maximum resident set size`` (kilobytes on Linux).
    """
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    r_out, w_out = os.pipe() if capture else (None, None)
    r_err, w_err = os.pipe() if capture else (None, None)
    t0 = time.time()
    pid = os.fork()
    if pid == 0:  # child
        try:
            if cwd:
                os.chdir(cwd)
            if capture:
                os.dup2(w_out, 1)
                os.dup2(w_err, 2)
                os.close(r_out)
                os.close(r_err)
            os.execvpe(argv[0], list(argv), full_env)
        except Exception:  # pragma: no cover - exec failure path
            os._exit(127)
    # parent
    out_data = b""
    err_data = b""
    if capture:
        os.close(w_out)
        os.close(w_err)
        # Drain pipes to avoid deadlock on large output.
        import select

        fds = [r_out, r_err]
        while fds:
            ready, _, _ = select.select(fds, [], [])
            for fd in ready:
                chunk = os.read(fd, 65536)
                if not chunk:
                    fds.remove(fd)
                    os.close(fd)
                elif fd == r_out:
                    out_data += chunk
                else:
                    err_data += chunk
    _, status, ru = os.wait4(pid, 0)
    wall = time.time() - t0
    exit_code = os.waitstatus_to_exitcode(status)
    oomed = 1 if exit_code in (137, -9) else 0
    return RunResult(
        wall,
        int(ru.ru_maxrss),
        exit_code,
        oomed,
        out_data.decode(errors="replace"),
        err_data.decode(errors="replace"),
    )


def docker_helios(
    helios_bin,
    store_dir,
    verb_args,
    image="debian:stable-slim",
    mem="6g",
    extra_mounts=None,
) -> RunResult:
    """Run a single helios verb inside ``docker run --rm -m <mem>`` and read peak RSS.

    Peak RSS comes from the container's cgroup-v2 ``memory.peak`` (bytes -> KB). An
    OOM kill surfaces as exit 137 -> ``oomed=1`` (a legitimate measured result at
    large sizes: it directly evidences the cli.go:118 whole-file-into-RAM ceiling).
    ``verb_args`` are the helios args already referencing container-internal paths
    (e.g. ``["commit", "--work", "/work"]``).
    """
    mounts = [
        "-v",
        f"{store_dir}:/store",
        "-v",
        f"{helios_bin}:/helios:ro",
    ]
    for host, cont, ro in extra_mounts or []:
        mounts += ["-v", f"{host}:{cont}" + (":ro" if ro else "")]
    inner = (
        "start=$(date +%s.%N); "
        + "/helios "
        + " ".join(verb_args)
        + " >/tmp/out 2>/tmp/err; rc=$?; "
        + "end=$(date +%s.%N); "
        + 'echo "__RC__ $rc"; '
        + 'echo "__WALL__ $(echo "$end - $start" | bc -l 2>/dev/null || python3 -c "print($end-$start)")"; '
        + 'echo "__PEAK__ $(cat /sys/fs/cgroup/memory.peak 2>/dev/null || echo 0)"; '
        + "cat /tmp/out"
    )
    argv = [
        "docker",
        "run",
        "--rm",
        "-m",
        mem,
        "--memory-swap",
        mem,
        # Run as the host user so materialized files are host-owned (cleanable) and
        # never left root-owned; the mounted /store,/work,/out dirs are host-owned.
        "--user",
        f"{os.getuid()}:{os.getgid()}",
        "-e",
        "HELIOS_STORE_DIR=/store",
        "-e",
        "HOME=/tmp",
        *mounts,
        image,
        "sh",
        "-c",
        inner,
    ]
    res = run_native(argv, capture=True)
    rc = None
    wall = res.wall_s
    peak_bytes = 0
    payload = []
    for line in res.stdout.splitlines():
        if line.startswith("__RC__ "):
            rc = int(line.split()[1])
        elif line.startswith("__WALL__ "):
            try:
                wall = float(line.split()[1])
            except (ValueError, IndexError):
                pass
        elif line.startswith("__PEAK__ "):
            try:
                peak_bytes = int(line.split()[1])
            except (ValueError, IndexError):
                peak_bytes = 0
        else:
            payload.append(line)
    # docker itself exits 137 on OOM kill; helios rc may be None if the container died.
    oomed = 1 if (res.exit_code == 137 or rc in (137, None)) else 0
    exit_code = rc if rc is not None else res.exit_code
    peak_kb = peak_bytes // 1024 if peak_bytes else res.peak_rss_kb
    return RunResult(
        wall, int(peak_kb), exit_code, oomed, "\n".join(payload), res.stderr
    )
