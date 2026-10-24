Import("env")
import os, subprocess

WEB = os.path.join(env["PROJECT_DIR"], "..", "web")


def build_web(*args, **kwargs):
    if not os.path.isdir(os.path.join(WEB, "node_modules")):
        subprocess.check_call(["pnpm", "install", "--frozen-lockfile"], cwd=WEB)
    subprocess.check_call(["pnpm", "build"], cwd=WEB)


env.AddPreAction("buildfs", build_web)  # runs before buildfs / uploadfs
env.AddCustomTarget(
    "web", None, build_web, title="Build web UI", description="pnpm build in web/"
)
