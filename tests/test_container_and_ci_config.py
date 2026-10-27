"""Static checks of the container and CI configuration. They prove properties of the FILES; they do NOT prove the image
builds or runs (the Docker daemon was unavailable). The CI job is what exercises the real build."""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = (ROOT / "Dockerfile").read_text("utf-8")
IGNORE = (ROOT / ".dockerignore").read_text("utf-8").splitlines()
CI = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml").read_text("utf-8"))
COMPOSE = yaml.safe_load((ROOT / "compose.yaml").read_text("utf-8"))


# ---------------------------------------------------------------- Dockerfile
def stages():
    return re.findall(r"^FROM\s+\S+\s+AS\s+(\w+)", DOCKERFILE, re.MULTILINE)


def test_base_image_is_pinned_by_digest():
    m = re.search(r"^ARG PYTHON_IMAGE=(\S+)", DOCKERFILE, re.MULTILINE)
    assert m and re.fullmatch(r"python:3\.11-slim-bookworm@sha256:[0-9a-f]{64}", m.group(1))
    assert "latest" not in DOCKERFILE.lower().replace("not latest", "")


def test_default_target_is_the_lexical_only_runtime():
    assert stages() == ["builder", "base", "semantic", "runtime"]  # the LAST stage is what `docker build` produces
    runtime = DOCKERFILE.split("FROM base AS runtime")[1]
    assert "pip install" not in runtime and "torch" not in runtime


def stage_text(name: str) -> str:
    parts = re.split(r"^FROM .* AS (\w+)\s*$", DOCKERFILE, flags=re.MULTILINE)
    return dict(zip(parts[1::2], parts[2::2], strict=True))[name]


def test_runs_as_non_root_with_a_healthcheck():
    base = stage_text("base")  # the default `runtime` stage adds nothing to it
    lines = [x.strip() for x in base.splitlines() if x.strip() and not x.strip().startswith("#")]
    assert "USER 10001:10001" in lines
    assert lines.index("USER 10001:10001") < next(i for i, x in enumerate(lines) if x.startswith("ENTRYPOINT"))
    assert not any(x.startswith("USER root") for x in lines)
    # the optional semantic stage briefly becomes root to install wheels and MUST drop back
    sem = [x.strip() for x in stage_text("semantic").splitlines() if x.strip() and not x.strip().startswith("#")]
    assert [x for x in sem if x.startswith("USER")] == ["USER root", "USER 10001:10001"]
    assert any(x.startswith("HEALTHCHECK") for x in lines) and "/healthz" in " ".join(lines)  # not just in a comment
    assert "useradd --system" in base and "nologin" in base
    assert stage_text("runtime").strip() == ""  # no extra instructions after the base

def test_dependencies_are_installed_hash_pinned_wheels_only():
    line = next(x for x in DOCKERFILE.splitlines() if "requirements-container.txt" in x and "pip install" in x)
    assert "--require-hashes" in line and "--only-binary=:all:" in line and "--no-deps" not in line


def instructions() -> str:
    """The Dockerfile without comment lines: what the build actually executes."""
    return "\n".join(x for x in DOCKERFILE.splitlines() if x.strip() and not x.lstrip().startswith("#"))


def test_no_model_download_or_secrets_in_the_image_recipe():
    code = instructions()
    for bad in ("snapshot_download", "fetch_model", "huggingface.co", "ADD http", "curl ", "wget ", "ENV AWS_",
                "COPY models", "COPY .env"):
        assert bad not in code, bad
    assert not re.search(r"(?i)\b(password|passwd|secret|api[_-]?key|credential|\w*_token|(access|auth)[_-]?token)\w*\s*[=:]", code)
    assert "HF_HUB_OFFLINE=1" in code and "TRANSFORMERS_OFFLINE=1" in code
    assert "models" not in "".join(x for x in code.splitlines() if x.startswith("COPY"))

def test_only_the_needed_files_are_copied_and_bundled_synthetic_data_is_included():
    copies = [x for x in DOCKERFILE.splitlines() if x.startswith("COPY ") and "--from" not in x]
    targets = " ".join(copies)
    assert "src/" in targets and "data/" in targets and "calibration/abstain_policy.json" in targets
    assert ".env" not in targets and "tests" not in targets


def test_non_loopback_listening_is_an_explicit_documented_opt_in():
    assert "CLAIMS_ALLOW_NONLOOPBACK=1" in DOCKERFILE and "127.0.0.1:7860:7860" in DOCKERFILE
    assert '"--host", "0.0.0.0"' in DOCKERFILE


def test_semantic_variant_is_optional_and_labelled_untested():
    sem = DOCKERFILE.split("FROM base AS semantic")[1].split("FROM base AS runtime")[0]
    assert "UNTESTED" in DOCKERFILE and "never downloads the model" in DOCKERFILE.replace("NEVER", "never")
    assert "download.pytorch.org/whl/cpu" in sem and "snapshot_download" not in sem


def test_dockerfile_discloses_that_it_was_not_built_locally():
    assert "has NOT been built" in DOCKERFILE


# ---------------------------------------------------------------- .dockerignore
@pytest.mark.parametrize("entry", [".git", ".venv", "models", "tests", ".env", "*.pem", "__pycache__", "eval", "demo_logs"])
def test_dockerignore_excludes_sensitive_or_heavy_paths(entry):
    assert entry in IGNORE


def test_dockerignore_does_not_exclude_what_the_image_needs():
    for needed in ("src", "data", "calibration", "requirements-container.txt"):
        assert needed not in [x for x in IGNORE if not x.startswith("!")], needed
    assert "!requirements-container.txt" in IGNORE


def test_image_layout_is_sufficient_to_run_the_app(tmp_path):
    """Copy exactly what the Dockerfile COPYs into an empty dir and run the service from there (no docker needed)."""
    for rel in ("src", "data"):
        shutil.copytree(ROOT / rel, tmp_path / rel, ignore=shutil.ignore_patterns("__pycache__"))
    (tmp_path / "calibration").mkdir()
    shutil.copy(ROOT / "calibration" / "abstain_policy.json", tmp_path / "calibration" / "abstain_policy.json")
    code = ("import sys; sys.path.insert(0, 'src')\n"
            "from claims_engine.demo_service import DemoService\n"
            "s = DemoService.build(); d = {x.filename: x.doc_id for x in s.documents()}\n"
            "r = s.assess('burst pipes sudden accidental escape water', [d['synthetic_home_policy.pdf']])\n"
            "print(len(s.documents()), r.result.assessment.status.value, s.policy_version)\n")
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    out = subprocess.run([sys.executable, "-I", "-c", code], cwd=tmp_path, env=env,
                         capture_output=True, text=True, timeout=120, check=False)
    assert out.returncode == 0, out.stderr
    assert out.stdout.split() == ["8", "potentially_covered", "cal-2026-10-27-v1"]


def test_container_requirements_are_fully_hash_pinned():
    text = (ROOT / "requirements-container.txt").read_text("utf-8")
    entries = re.findall(r"^([a-z0-9_.-]+)==([^\s\\]+) \\\n((?:\s+--hash=sha256:[0-9a-f]{64}(?: \\)?\n?)+)", text, re.MULTILINE)
    names = [e[0] for e in entries]
    assert len(names) == len(set(names)) >= 60
    for required in ("gradio", "starlette", "pydantic", "pymupdf", "numpy", "langgraph", "fastapi", "uvicorn"):
        assert required in names, required
    non_comment = [x for x in text.splitlines() if x and not x.startswith("#") and not x.startswith(" ")]
    assert all("==" in x for x in non_comment)  # nothing unpinned
    assert "torch" not in names and "sentence-transformers" not in names  # default image is lexical-only


def test_container_requirements_match_the_demo_pins():
    text = (ROOT / "requirements-container.txt").read_text("utf-8")
    gradio = re.search(r"^gradio==(\S+) ", text, re.MULTILINE).group(1)
    assert f"gradio=={gradio}" in (ROOT / "requirements-demo.txt").read_text("utf-8")
    assert re.search(r"^starlette==1\.", text, re.MULTILINE)  # the Starlette advisories are fixed in 1.x


# ---------------------------------------------------------------- compose
def test_compose_publishes_to_loopback_only_and_drops_privileges():
    for name, svc in COMPOSE["services"].items():
        assert all(p.startswith("127.0.0.1:") for p in svc["ports"]), name
        assert svc["read_only"] is True and svc["cap_drop"] == ["ALL"], name
        assert "no-new-privileges:true" in svc["security_opt"], name
        assert svc["mem_limit"] and svc["pids_limit"], name
        assert "environment" not in svc or not svc["environment"], name  # no credentials


def test_compose_semantic_variant_is_a_profile_with_a_read_only_model_mount():
    sem = COMPOSE["services"]["demo-semantic"]
    assert sem["profiles"] == ["semantic"]
    assert any(v.endswith(":/app/models:ro") for v in sem["volumes"])
    assert "volumes" not in COMPOSE["services"]["demo"]


# ---------------------------------------------------------------- GitHub Actions
def steps_of(job):
    return CI["jobs"][job]["steps"]


def test_workflow_has_least_privilege_and_no_dangerous_triggers():
    triggers = CI.get("on", CI.get(True))
    assert "pull_request_target" not in triggers and "workflow_run" not in triggers
    assert CI["permissions"] == {"contents": "read"}
    assert all("timeout-minutes" in j for j in CI["jobs"].values())


def test_every_third_party_action_is_pinned_to_a_full_commit_sha():
    uses = [s["uses"] for j in CI["jobs"] for s in steps_of(j) if "uses" in s]
    assert uses and all(re.fullmatch(r"actions/[\w-]+@[0-9a-f]{40}", u) for u in uses), uses


def test_checkout_does_not_persist_credentials():
    for j in CI["jobs"]:
        for s in steps_of(j):
            if s.get("uses", "").startswith("actions/checkout"):
                assert s["with"]["persist-credentials"] is False


def test_no_secrets_are_referenced_and_no_curl_pipe_shell():
    raw = (ROOT / ".github" / "workflows" / "ci.yml").read_text("utf-8")
    assert "secrets." not in raw and "| sh" not in raw and "| bash" not in raw


def test_ci_runs_the_same_gates_as_the_local_milestone_checks():
    run = "\n".join(s.get("run", "") for s in steps_of("quality"))
    for cmd in ("pip check", "ruff check .", "ruff check --select S src scripts", "mypy src", "pytest -q"):
        assert cmd in run, cmd
    assert "requirements-dev.txt" in run and "requirements-embeddings" not in run  # lexical-only; no model in CI


def test_ci_audits_dependencies_and_smoke_tests_the_container():
    audit = "\n".join(s.get("run", "") for s in steps_of("dependency-audit"))
    assert "pip-audit" in audit and "requirements-container.txt" in audit and "--disable-pip" in audit
    assert re.search(r'pip-audit==\d+\.\d+\.\d+', audit)  # tool version pinned
    cont = "\n".join(s.get("run", "") for s in steps_of("container"))
    for needle in ("docker build --target runtime", "/healthz", "--read-only", "--cap-drop ALL",
                   "10001:10001", "content-security-policy", "test ! -e /app/models"):
        assert needle.lower() in cont.lower(), needle
    assert CI["jobs"]["container"]["needs"] == "quality"


def test_ci_does_not_download_the_model_or_call_paid_services():
    raw = (ROOT / ".github" / "workflows" / "ci.yml").read_text("utf-8").lower()
    for bad in ("fetch_model", "huggingface", "elevenlabs", "aws ", "aws-actions", "api_key"):
        assert bad not in raw, bad


def test_dependabot_covers_pip_actions_and_docker():
    cfg = yaml.safe_load((ROOT / ".github" / "dependabot.yml").read_text("utf-8"))
    assert {u["package-ecosystem"] for u in cfg["updates"]} == {"pip", "github-actions", "docker"}