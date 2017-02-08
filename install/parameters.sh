# Inputs:
#   $USER
#   $TOUCH_MAPPER_DEV_ENV (optional)
# Outputs:
#   $env_name
#   $stack_name (cloudformation stack)
#   $is_dev_env (true | false)
#   $domain (CloudFront and S3)

if [[ $# != 1 ]]; then
    echo "Usage: $0 ENVIRONMENT"
    exit 1
fi
environment=$1

if [[ $environment == dev ]]; then
    dev_env=${TOUCH_MAPPER_DEV_ENV:-$USER}
    if [[ ! $dev_env ]]; then
        echo "Environment variables TOUCH_MAPPER_DEV_ENV and USER are both unset, aborting"
    fi
    echo env_name=dev-$dev_env
    echo stack_name=TouchMapperDev${dev_env^}
    echo is_dev_env=true
    echo domain=dev-$dev_env.touch-mapper-481.org
else
    echo env_name=$environment
    echo stack_name=TouchMapper${environment^}
    echo is_dev_env=false
    if [[ $environment == prod ]]; then
        echo domain=touch-mapper-481.org
    else
        echo domain=$environment.touch-mapper-481.org
    fi
fi


