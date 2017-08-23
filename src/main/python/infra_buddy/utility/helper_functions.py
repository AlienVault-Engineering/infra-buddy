from operator import itemgetter

import boto3

from infra_buddy.aws.cloudformation import CloudFormationBuddy


def _get_all_export_values(client):
    pass


def load_balancer_name(deploy_ctx):
    # type: (DeployContext) -> str
    cf = CloudFormationBuddy(deploy_ctx)
    # we need an export value from the cluster stack so manually override it
    val = _get_cluster_stack_export_value(cf, deploy_ctx,"ElasticLoadBalancerARN")
    # //#amazon conveniently wants some substring of the ARN instead of the name or other value actually available in the API
    # //# turn arn:aws: elasticloadbalancing: us-west-2: 271083817914: listener/app/prod-EcsEl-1WYNMMT2MT9NR/c5f92ddeb151227f/313bb2e23d9dd8d8
    # //# into app/prod-EcsEl-1WYNMMT2MT9NR/c5f92ddeb151227f/313bb2e23d9dd8d8
    return "" if not val else val[val.find('app/')+4:]


def _get_cluster_stack_export_value(cf, deploy_ctx, param):
    # type: (CloudFormationBuddy,DeployContext) -> str
    cf.stack_name = deploy_ctx.cluster_stack_name
    val = cf.get_export_value(param)
    return val


def calculate_rule_priority(deploy_ctx,stack_name):
    # type: (DeployContext,str) -> str
    cf = CloudFormationBuddy(deploy_ctx)
    # we need some data for the passed stack_name so manually override it
    cf.stack_name = deploy_ctx.stack_name
    if cf.does_stack_exist():
        return cf.get_existing_parameter_value('RulePriority')
    else:
        listenerArn = _get_cluster_stack_export_value(cf,deploy_ctx,"ListenerARN")
        client = boto3.client('elbv2',region_name=deploy_ctx.region)
        rules = client.describe_rules(ListenerArn=listenerArn)
        if not rules or len(rules)==0:
            current_max = 30
        else:
            rules = sorted(rules, key=itemgetter("Priority"),reverse=True)
            current_max = int(rules[0]['Priority'])
        return str(current_max+1)


    # //if [[ $(does_stack_exist ${STACK_NAME}) == "Yes" ]]; then
    # //    RULE_PRIORITY=$(print_stack_param ${STACK_NAME} "RulePriority")
    # //else
    # //    ListenerARN=`print_export_value "$(generate_cluster_stack_name)-ListenerARN"`
    # //    EXISTING_RULES=`aws elbv2 describe-rules --listener-arn ${ListenerARN} | jq ".Rules"`
    # //    if [[ ${EXISTING_RULES} != "null" ]]; then
    # //        CURRENT_MAX=$(aws elbv2 describe-rules --listener-arn ${ListenerARN} | jq ".Rules[].Priority" | sed 's/[^0-9]*//g' | sort -nr | head -n1)
    # //    else
    # //        CURRENT_MAX=30
    # //    fi
    # //    #increment by 30 to allow plenty of room for explicit rule creation
    # //    CURRENT_NUMBER_OF_RULES=$((CURRENT_MAX+1))
    # //fi
