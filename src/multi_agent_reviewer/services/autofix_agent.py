import logging
from multi_agent_reviewer.utils.github_utils import (
    clone_github_repo,
    run_command,
    get_installation_token,
)


def apply_suggestion_patch(owner, repo, pr_number, installation_id, suggestion):
    """
    Clone the repo, apply the patch, commit, and push to the PR branch.
    """
    head_sha = suggestion.get("head_sha")
    patch = suggestion["patch"]
    file_path = suggestion["file"]
    # Clone repo
    tempdir, repo_dir = clone_github_repo(owner, repo, head_sha, installation_id)
    patch_file = f"{repo_dir}/patch.diff"
    with open(patch_file, "w") as f:
        f.write(patch)
    # Apply patch
    res = run_command(["git", "apply", patch_file], cwd=repo_dir)
    if res["returncode"] != 0:
        logging.error(f"Failed to apply patch: {res['stderr']}")
        return False
    # Commit and push
    run_command(["git", "add", file_path], cwd=repo_dir)
    run_command(
        ["git", "commit", "-m", f"Apply suggestion {suggestion['id']}"], cwd=repo_dir
    )
    run_command(["git", "push", "origin", f"HEAD:{head_sha}"], cwd=repo_dir)
    logging.info(f"Applied suggestion {suggestion['id']} and pushed to PR branch.")
    return True
