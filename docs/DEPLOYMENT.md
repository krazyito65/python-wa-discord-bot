# Documentation Deployment Guide

This guide explains how to deploy the WeakAuras Discord Bot documentation to GitHub Pages.

## Automatic Deployment (Recommended)

The documentation is automatically built and deployed using GitHub Actions whenever code is pushed to the `main` branch.

### Setup Steps

1. **Enable GitHub Pages**
   - Go to your repository's Settings → Pages
   - Under "Source", select "GitHub Actions"
   - The workflow will handle the rest automatically

2. **Workflow Triggers**
   The documentation builds automatically when:
   - Python files (`**/*.py`) are changed
   - Documentation files (`docs/**`) are changed
   - Workflow file (`.github/workflows/docs.yml`) is changed
   - Dependencies (`pyproject.toml`, `uv.lock`) are changed

3. **Access Documentation**
   After deployment, your documentation will be available at:
   ```
   https://{username}.github.io/{repository-name}/
   ```

## Manual Deployment

If you need to manually trigger a deployment:

1. **Via GitHub Interface**
   - Go to Actions tab in your repository
   - Find "Build and Deploy Documentation" workflow
   - Click "Run workflow" → "Run workflow"

2. **Via Local Build and Push**
   ```bash
   # Build documentation locally
   cd docs && uv run sphinx-build -b html . _build/html

   # Commit and push changes
   git add .
   git commit -m "Update documentation"
   git push origin main
   ```

## Workflow Details

### Build Process
1. **Environment Setup**
   - Ubuntu latest runner
   - Python 3.13
   - uv package manager

2. **Documentation Generation**
   - Install dependencies via `uv sync`
   - Generate API docs with `sphinx-apidoc`
   - Build HTML docs with `sphinx-build`

3. **Deployment** (main branch only)
   - Upload artifacts to GitHub Pages
   - Deploy using official GitHub Pages action

### Branch Behavior
- **Main Branch**: Full build + deployment to GitHub Pages
- **Other Branches/PRs**: Build only (no deployment)
- **Manual Trigger**: Available from any branch

## Customization

### Custom Domain
To use a custom domain:
1. Add `CNAME` file to `docs/` directory:
   ```
   docs.example.com
   ```
2. Configure DNS to point to GitHub Pages
3. Enable custom domain in repository Settings → Pages

### Build Configuration
Edit `.github/workflows/docs.yml` to:
- Change trigger conditions
- Modify build steps
- Add additional checks

### Sphinx Configuration
Modify `docs/conf.py` to:
- Change theme or styling
- Add extensions
- Configure build options

## Troubleshooting

### Build Failures
Check the Actions tab for detailed error logs:
- **Import Errors**: Missing dependencies in `docs/requirements.txt`
- **Sphinx Errors**: Check `docs/conf.py` configuration
- **API Doc Errors**: Verify Python module structure

### Deployment Issues
- **404 Errors**: Check GitHub Pages source settings
- **Style Issues**: Verify `.nojekyll` file exists
- **Permissions**: Ensure workflow has Pages write permissions

### Local Testing
Test documentation locally before pushing:
```bash
# Build documentation
cd docs && uv run sphinx-build -b html . _build/html

# Serve locally
uv run python serve_docs.py

# Check for warnings/errors in build output
```

## Security Considerations

- The workflow only has access to public repository content
- No secrets or tokens are required for documentation builds
- Documentation is publicly accessible via GitHub Pages
- Ensure no sensitive information is included in docstrings or docs

## Monitoring

- **Build Status**: Check green checkmarks on commits
- **Deploy Status**: Monitor Actions tab for deployment logs
- **Site Status**: Visit the GitHub Pages URL to verify deployment
- **Analytics**: Consider adding Google Analytics to track usage
