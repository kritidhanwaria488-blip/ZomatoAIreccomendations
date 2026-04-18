# Rollback Instructions

## Changes Made in This Session:

### Files Created:
1. `streamlit_app.py` - Streamlit deployment file
2. `.streamlit/config.toml` - Streamlit configuration
3. `.streamlit/secrets.toml.example` - Secrets template
4. `requirements.txt` - Dependencies
5. `STREAMLIT_DEPLOY.md` - Deployment guide
6. `TODO_TOMORROW.md` - Todo list
7. `check_data.py` - Data checker
8. `ROLLBACK.md` - This file

### Files Modified:
1. `frontend/next.config.ts` - Added static export
2. `.gitignore` - Added Streamlit secrets
3. `pyproject.toml` - Added Streamlit dependencies
4. `docs/phase-wise-architecture.md` - Added deployment section
5. `DEPLOYMENT.md` - Added Streamlit deployment
6. `frontend/src/app/page.tsx` - Removed rating note
7. `frontend/src/app/components/SearchForm.tsx` - Changed rating label

### Commits to Revert:
- "Add restaurant dataset (12,119 restaurants) for Streamlit deployment"
- "Add Streamlit Cloud deployment support - streamlit_app.py, config, requirements, and deployment guide"

---

## How to Rollback:

### Option 1: Hard Reset (Nuclear Option)
```bash
cd c:/Users/Kriti/OneDrive/Desktop/milestone1

# Reset to initial commit
git reset --hard 5415190

# Force push (WARNING: This deletes commits on GitHub!)
git push origin main --force
```

### Option 2: Soft Reset (Keeps Changes as Uncommitted)
```bash
cd c:/Users/Kriti/OneDrive/Desktop/milestone1

# Reset to initial commit but keep files
git reset --soft 5415190

# Now manually delete files you don't want:
del streamlit_app.py
del requirements.txt
del TODO_TOMORROW.md
del check_data.py
del ROLLBACK.md
rmdir /s .streamlit

# Restore modified files from initial commit
git checkout 5415190 -- frontend/next.config.ts

git checkout 5415190 -- .gitignore

git checkout 5415190 -- pyproject.toml

git checkout 5415190 -- docs/phase-wise-architecture.md

git checkout 5415190 -- DEPLOYMENT.md

git checkout 5415190 -- frontend/src/app/page.tsx

git checkout 5415190 -- frontend/src/app/components/SearchForm.tsx

# Commit the restored state
git add .
git commit -m "Rollback to initial state"
git push origin main --force
```

### Option 3: Revert Individual Commits
```bash
cd c:/Users/Kriti/OneDrive/Desktop/milestone1

# Revert the last two commits
git revert 3129008 --no-edit
git revert 6055a76 --no-edit

# Push
git push origin main
```

---

## After Rollback:

You will be back to the initial state with:
- ✅ All 5 phases code complete
- ✅ FastAPI backend ready
- ✅ Next.js frontend ready
- ❌ No Streamlit deployment files
- ❌ No deployment guides
- ❌ Frontend UI labels as they were originally

---

## Recommendation:

**Use Option 3 (Revert)** - It's the safest and cleanest approach.

```bash
cd c:/Users/Kriti/OneDrive/Desktop/milestone1
git revert 3129008 --no-edit
git revert 6055a76 --no-edit
git push origin main
```

This will undo the deployment changes while keeping a record of what was done.
