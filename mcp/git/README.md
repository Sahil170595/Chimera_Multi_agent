# Git MCP Server

Purpose: expose basic git operations to models via MCP (stdio).

## Tools
- file.write: write file content
- git.commit: commit staged changes
- git.push: push to remote/branch
- git.sha: current commit SHA

## Auth
- Uses local git config / environment. No secrets stored in code.
