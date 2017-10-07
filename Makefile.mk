#
#   Copyright 2015  Xebia Nederland B.V.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
NAME=$(shell basename $(PWD))

RELEASE_SUPPORT := $(shell dirname $(abspath $(lastword $(MAKEFILE_LIST))))/.make-release-support

VERSION=$(shell . $(RELEASE_SUPPORT) ; getVersion)
TAG=$(shell . $(RELEASE_SUPPORT); getTag)

SHELL=/bin/bash

.PHONY: pre-build do-build post-build build release patch-release minor-release major-release tag check-status check-release showver \
	upload do-upload post-upload

build: pre-build do-build post-build

pre-build:


post-build:


do-build: venv
	. venv/bin/activate && python setup.py check
	. venv/bin/activate && python setup.py build

.release:
	@echo "release=0.0.0" > .release
	@(if [ ! -d .git ] ; then echo "tag=$(NAME)-0.0.0"; else echo tag=v0.0.0 ; fi) >> .release
	@echo INFO: .release created
	@cat .release


release: check-status check-release build upload


upload: do-upload post-upload 

do-upload: 
	rm -rf dist/*
	. venv/bin/activate && python setup.py sdist
	. venv/bin/activate && twine upload dist/*

snapshot: build upload

showver: .release
	@. $(RELEASE_SUPPORT); getVersion

tag-patch-release: VERSION := $(shell . $(RELEASE_SUPPORT); nextPatchLevel)
tag-patch-release: .release tag 

tag-minor-release: VERSION := $(shell . $(RELEASE_SUPPORT); nextMinorLevel)
tag-minor-release: .release tag 

tag-major-release: VERSION := $(shell . $(RELEASE_SUPPORT); nextMajorLevel)
tag-major-release: .release tag 

patch-release: tag-patch-release release
	@echo $(VERSION)

minor-release: tag-minor-release release
	@echo $(VERSION)

major-release: tag-major-release release
	@echo $(VERSION)


tag: TAG=$(shell . $(RELEASE_SUPPORT); getTag $(VERSION))
tag: check-status
	@. $(RELEASE_SUPPORT) ; ! tagExists $(TAG) || (echo "ERROR: tag $(TAG) for version $(VERSION) already tagged in git" >&2 && exit 1) ;
	@. $(RELEASE_SUPPORT) ; setRelease $(VERSION)
	git add .
	git commit -m "bumped to version $(VERSION)" ;
	git tag $(TAG) ;
	@[ -n "$(shell git remote -v)" ] && git push --tags

check-status:
	@. $(RELEASE_SUPPORT) ; ! hasChanges || (echo "ERROR: there are still outstanding changes" >&2 && exit 1) ;

check-release: .release
	@. $(RELEASE_SUPPORT) ; tagExists $(TAG) || (echo "ERROR: version not yet tagged in git. make [minor,major,patch]-release." >&2 && exit 1) ;
	@. $(RELEASE_SUPPORT) ; ! differsFromRelease $(TAG) || (echo "ERROR: current directory differs from tagged $(TAG). make [minor,major,patch]-release." ; exit 1)

venv: 
	virtualenv venv  && \
        . ./venv/bin/activate && \
        pip --quiet install --upgrade pip  && \
	pip install --upgrade setuptools twine

clean:
	python setup.py clean
	rm -rf build/* dist/*  *.egg-info

clobber: clean
	rm -rf venv

test: do-build
	@. venv/bin/activate && python setup.py test
	
autopep:
	autopep8 --experimental --in-place --max-line-length 132 $(shell find . -name \*.py   | grep -v -e /.eggs/ -e /venv/ -e /build/ -e /dist/)

