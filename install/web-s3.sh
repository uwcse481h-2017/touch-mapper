#!/bin/bash

set -e

if [[ $# != 1 ]]; then
    echo "Usage: $0 ENVIRONMENT"
    exit 1
fi
environment=$1

cd "$( dirname "${BASH_SOURCE[0]}" )"
cd ../web
eval $( ../install/parameters.sh $environment )
url=s3://$domain
echo "env_name: $env_name"
echo "S3 web bucket: $url"
./create-env-js.sh $env_name >build/scripts/environment.js 

# build => dist
# Changes call to rename from "rename 's/\.html//' *.html" because 
# we are using a newer version of the rename package
rm -rf dist
cp -a build dist
for lang in $(cd dist; find ?? -type d); do
    (
        cd dist/$lang
        rename .html '' *.html
        mv index index.html
    )
done
rm -f dist/.gitignore


# Sync dist to S3
aws s3 sync --delete --cache-control must-revalidate dist/ $url
for lang in $( cd dist; find ?? -maxdepth 0 -type d ); do
    aws s3 rm --quiet --recursive $url/$lang
    aws s3 sync --cache-control must-revalidate --content-type text/html dist/$lang/ $url/$lang
done


# Invalidate CloudFront
distribution_id=$( aws cloudfront list-distributions | jq --raw-output ".DistributionList.Items[] | select(.Origins.Items[].DomainName == \"$env_name.maps.touch-mapper.s3.amazonaws.com\") | .Id" )
echo "Invalidating $env_name environment CloudFront distribution '$distribution_id'"
aws cloudfront create-invalidation --distribution-id $distribution_id --paths '/*'

echo "Web resources installed to https://$( cat dist/scripts/environment.js  | egrep '^window.TM_DOMAIN' | cut -d "'" -f 2 )"

