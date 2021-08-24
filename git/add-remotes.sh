#!/bin/bash
# purpose: add all remotes for repo
# author: Jeff Reeves

# define repository's stub for the URL
REPO_STUB='laundromatic'

# create the repo directory on bridges
ssh git@bridges "mkdir /git/laundromatic.git && cd /git/laundromatic.git && git config --global init.defaultBranch main && git init --bare && sed -i 's/master/main/' /git/rpi4-custom-os.git/HEAD"

# add bridges to git remote list
git remote add bridges git@bridges:/git/laundromatic.git

# add gitlab to git remote list
git remote add gitlab git@gitlab.com:JeffReeves/laundromatic.git

# add github to git remote list
git remote add github git@github.com:JeffReeves/laundromatic.git

# update origin to bridges
git remote set-url origin git@bridges:/git/laundromatic.git

# view all remotes
git remote -v

# open settings for gitlab and github in browser
#explorer.exe "https://gitlab.com/JeffReeves/laundromatic/-/settings/repository"
#explorer.exe "https://gitlab.com/JeffReeves/laundromatic/-/branches"
#explorer.exe "https://github.com/JeffReeves/laundromatic/settings/branches"
#explorer.exe "https://github.com/JeffReeves/laundromatic/branches"

