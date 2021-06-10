from invoke import run as local
from fabric import task
from patchwork.transfers import rsync

exclude_dirs = [".git", "node_modules", ".cache", ".github", "db.sqlite3",
                ".env", "*.yaml", ".venv"]

app_name = "github-search-candidates"
dest_dir = f"~/apps/{app_name}"

@task
def deploy(ctx):
    local("find . -name '__pycache__' |xargs rm -rf ", echo=True)
    rsync(ctx, ".", dest_dir, exclude=exclude_dirs)
    with ctx.cd(dest_dir):
        with ctx.prefix(f"source {dest_dir}/.env/bin/activate"):
            ctx.run("pip install -r requirements.txt")
    ctx.run(f"sudo supervisorctl restart {app_name}")


