import math
from operator import itemgetter

import boto3

from infra_buddy.aws.cloudformation import CloudFormationBuddy
from infra_buddy.utility import print_utility


def _get_all_export_values(client):
    pass


def load_balancer_name(deploy_ctx):
    # type: (DeployContext) -> str
    cf = CloudFormationBuddy(deploy_ctx)
    # we need an export value from the cluster stack so manually override it
    val = _get_cluster_stack_export_value(cf, deploy_ctx, "ElasticLoadBalancerARN")
    # //#amazon conveniently wants some substring of the ARN instead of the name or other value actually available in the API
    # //# turn arn:aws:elasticloadbalancing:us-west-2:271083817914:listener/app/prod-EcsEl-1WYNMMT2MT9NR/c5f92ddeb151227f/313bb2e23d9dd8d8
    # //# into app/prod-EcsEl-1WYNMMT2MT9NR/c5f92ddeb151227f/313bb2e23d9dd8d8
    return "" if not val else val[val.find('app/'):]


def _get_cluster_stack_export_value(cf, deploy_ctx, param):
    # type: (CloudFormationBuddy,DeployContext) -> str
    val = None
    try:
        cf.stack_name = deploy_ctx.cluster_stack_name
        val = cf.get_export_value(param)
    except Exception as e:
        print_utility.warn("Exception getting export for helper function - {}".format(e))
    finally:
        return val


def _get_max_priority(rules):
    rules = sorted(rules, key=lambda k: k["Priority"], reverse=True)
    for rule in rules:
        priority_ = rule['Priority']
        if priority_ != "default":
            return int(priority_)


# 0.5GB, 1GB, 2GB - Available cpu values: 256 (.25 vCPU)
# 1GB, 2GB, 3GB, 4GB - Available cpu values: 512 (.5 vCPU)
# 2GB, 3GB, 4GB, 5GB, 6GB, 7GB, 8GB - Available cpu values: 1024 (1 vCPU)
# Between 4GB and 16GB in 1GB increments - Available cpu values: 2048 (2 vCPU)
# Between 8GB and 30GB in 1GB increments - Available cpu values: 4096 (4 vCPU)
def _get_valid_fargate_memory(_value):
    if _value <= 512:
        print_utility.info("Transforming memory value of {} to '0.5GB' - min value".format(_value))
        return '0.5'
    elif _value < 1024:
        print_utility.info("Transforming memory value of {} to '1GB' - next legitimate value".format(_value))
        return '1'
    else:
        memory = int(math.ceil(_value/1024.0))
        if memory > 30:
            print_utility.info("Transforming memory value of {} to '30GB' - max value".format(_value))
            memory = 30
        else:
            print_utility.info("Transforming memory value of {} to '{}GB'".format(_value, memory))
        return memory


def _get_valid_fargate_cpu(_value):
    if _value <= 256:
        print_utility.info("Transforming cpu value of {} to '256' - min value".format(_value))
        return 256
    elif _value <= 512:
        print_utility.info("Transforming cpu value of {} to '512' - next valid value".format(_value))
        return 512
    elif _value <= 1024:
        print_utility.info("Transforming cpu value of {} to '1024' - next valid value".format(_value))
        return 1024
    elif _value <= 2048:
        print_utility.info("Transforming cpu value of {} to '2048' - next valid value".format(_value))
        return 2048
    elif _value <= 4096:
        print_utility.info("Transforming cpu value of {} to '4096' - next valid value".format(_value))
        return 4096
    else:
        print_utility.info("Transforming cpu value of {} to '4096' - max valid value".format(_value))
        return 4096


# 256 (.25 vCPU) - Available memory values: 0.5GB, 1GB, 2GB
# 512 (.5 vCPU) - Available memory values: 1GB, 2GB, 3GB, 4GB
# 1024 (1 vCPU) - Available memory values: 2GB, 3GB, 4GB, 5GB, 6GB, 7GB, 8GB
# 2048 (2 vCPU) - Available memory values: Between 4GB and 16GB in 1GB increments
# 4096 (4 vCPU) - Available memory values: Between 8GB and 30GB in 1GB increments
_valid_fargate_resources = {
    256: ['0.5GB', '1GB', '2GB'],
    512: ["{}GB".format(i) for i in range(1, 4)],
    1024: ["{}GB".format(i) for i in range(2, 8)],
    2048: ["{}GB".format(i) for i in range(4, 16)],
    4096: ["{}GB".format(i) for i in range(8, 30)],
}

_valid_fargate_memories = set([item for sublist in _valid_fargate_resources.itervalues() for item in sublist])



def _validate_fargate_resource_allocation(cpu, memory, deploy_ctx):
    if cpu is None:
        discovered_cpu = deploy_ctx.get('TASK_CPU', None)
        if discovered_cpu not in _valid_fargate_resources:
            print_utility.info('Skipping fargate resource validation - CPU not transformed - {}'.format(discovered_cpu))
            return
        cpu = discovered_cpu
    elif memory is None:
        discovered_memory = deploy_ctx.get('TASK_SOFT_MEMORY', None)
        if discovered_memory not in _valid_fargate_memories:
            print_utility.info(
                'Skipping fargate resource validation - Memory not transformed - {}'.format(discovered_memory))
            return
        memory = discovered_memory
    memory_possibilities = _valid_fargate_resources[cpu]
    if memory not in memory_possibilities:
        print_utility.error(
            'Attempting to use fargate with invalid configuration.  {} CPU {} Memory'.format(cpu, memory),
            raise_exception=True)


def transform_fargate_cpu(deploy_ctx, _value):
    if _using_fargate(deploy_ctx):
        cpu = _get_valid_fargate_cpu(_value)
        _validate_fargate_resource_allocation(cpu, None, deploy_ctx)
        return cpu


def _using_fargate(deploy_ctx):
    return deploy_ctx.get('USE_FARGATE', 'false') == 'true'


def transform_fargate_memory(deploy_ctx, _value):
    if _using_fargate(deploy_ctx):
        if isinstance(_value, basestring) and 'GB' in _value:
            if _value not in _valid_fargate_memories:
                print_utility.error(
                    'Attempting to use fargate with invalid memory.  {} Memory Valid Values: {}'.format(_value,
                                                                                                        _valid_fargate_memories),
                    raise_exception=True)
            else:
                memory = _value
        else:
            # transform from MB to GB
            memory = "{}GB".format(_get_valid_fargate_memory(_value))
        _validate_fargate_resource_allocation(None, memory, deploy_ctx)
        return memory


def calculate_rule_priority(deploy_ctx, stack_name):
    # type: (DeployContext,str) -> str
    cf = CloudFormationBuddy(deploy_ctx)
    # we need some data for the passed stack_name so manually override it
    cf.stack_name = stack_name
    if cf.does_stack_exist():
        return cf.get_existing_parameter_value('RulePriority')
    else:
        listenerArn = _get_cluster_stack_export_value(cf, deploy_ctx, "ListenerARN")
        if listenerArn:
            client = get_boto_client(deploy_ctx)
            rules = client.describe_rules(ListenerArn=listenerArn)['Rules']
        else:
            rules = None
        if not rules or len(rules) == 0:
            current_max = 30
        else:
            if len(rules) == 1 and rules[0]['Priority'] == "default":
                current_max = 30
            else:
                current_max = int(_get_max_priority(rules))
        return str(current_max + 1)

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


def get_boto_client(deploy_ctx):
    return boto3.client('elbv2', region_name=deploy_ctx.region)
