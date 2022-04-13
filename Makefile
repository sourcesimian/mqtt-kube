REGISTRY=
REPO=sourcesimian/mqtt-kube
TAG=$(shell cat version)

check:
	flake8 ./mqtt_kube --ignore E501
	find ./mqtt_kube -name '*.py' \
	| xargs pylint -d invalid-name \
	               -d missing-docstring \
	               -d too-few-public-methods \
	               -d line-too-long \
	               -d too-many-arguments \
	               -d too-many-instance-attributes \
	               -d no-self-use

test:
	pytest ./tests/ -vvv --junitxml=./reports/unittest-results.xml

docker-armv6:
	$(eval REPOTAG := ${REGISTRY}${REPO}:${TAG}-armv6)
	docker buildx build \
	    --platform linux/arm/v6 \
	    --load \
	    -t ${REPOTAG} \
	    -f docker/Dockerfile.alpine \
	    .

docker-amd64:
	$(eval REPOTAG := ${REGISTRY}${REPO}:${TAG}-amd64)
	docker buildx build \
	    --platform linux/amd64 \
	    --load \
	    -t ${REPOTAG} \
	    -f docker/Dockerfile.alpine \
	    .

push: docker-armv6 docker-amd64
	$(eval REPOTAG := ${REGISTRY}${REPO}:${TAG})
	$(eval LATEST := ${REGISTRY}${REPO}:latest)
	docker push ${REPOTAG}-amd64
	docker push ${REPOTAG}-armv6

	docker manifest rm ${REPOTAG} &>/dev/null || true
	docker manifest create \
	    ${REPOTAG} \
	    --amend ${REPOTAG}-amd64 \
	    --amend ${REPOTAG}-armv6
	docker manifest push ${REPOTAG}

	docker manifest rm ${LATEST} &>/dev/null || true
	docker manifest create \
	    ${LATEST} \
	    --amend ${REPOTAG}-amd64 \
	    --amend ${REPOTAG}-armv6
	docker manifest push ${LATEST}

run-armv6:
	docker run -it --rm -p 8080:8080 --volume ${KUBECONFIG}:/kubeconfig --env KUBECONFIG=/kubeconfig ${REGISTRY}${REPO}:${TAG}-armv6

run-amd64:
	docker run -it --rm -p 8080:8080 --volume ${KUBECONFIG}:/kubeconfig --env KUBECONFIG=/kubeconfig ${REGISTRY}${REPO}:${TAG}-amd64
