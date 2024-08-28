#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from cmk.ccc.version import Edition

from cmk.gui.form_specs.vue.visitors._registry import form_spec_registry
from cmk.gui.quick_setup.config_setups.aws.ruleset_helper import formspec_aws_tags
from cmk.gui.utils.rule_specs.loader import LoadedRuleSpec

from cmk.plugins.aws.lib import aws_region_to_monitor  # pylint: disable=cmk-module-layer-violation

try:
    # Ignore import-untyped for non-CCE CI stages
    from .cce import (  # type: ignore[import-untyped,unused-ignore]
        edition_specific_global_services,
        edition_specific_regional_services,
    )
except ImportError:
    from .cre import (
        edition_specific_global_services,
        edition_specific_regional_services,
    )

from cmk.rulesets.v1 import Help, Message, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    FieldSize,
    Integer,
    MultipleChoice,
    MultipleChoiceElement,
    Password,
    SingleChoice,
    SingleChoiceElement,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _global_services() -> Sequence[MultipleChoiceElement]:
    return [
        MultipleChoiceElement(name="ce", title=Title("Costs and usage (CE)")),
        *edition_specific_global_services(),
    ]


def _regional_services() -> Sequence[MultipleChoiceElement]:
    return [
        MultipleChoiceElement(name="ec2", title=Title("Elastic Compute Cloud (EC2)")),
        MultipleChoiceElement(name="ebs", title=Title("Elastic Block Storage (EBS)")),
        MultipleChoiceElement(name="s3", title=Title("Simple Storage Service (S3)")),
        MultipleChoiceElement(name="glacier", title=Title("Amazon S3 Glacier (Glacier)")),
        MultipleChoiceElement(name="elb", title=Title("Classic Load Balancing (ELB)")),
        MultipleChoiceElement(
            name="elbv2", title=Title("Application and Network Load Balancing (ELBv2)")
        ),
        MultipleChoiceElement(name="rds", title=Title("Relational Database Service (RDS)")),
        MultipleChoiceElement(name="cloudwatch_alarms", title=Title("CloudWatch Alarms")),
        MultipleChoiceElement(name="dynamodb", title=Title("DynamoDB")),
        MultipleChoiceElement(name="wafv2", title=Title("Web Application Firewall (WAFV2)")),
        *edition_specific_regional_services(),
    ]


def _formspec_aws_api_access() -> dict[str, DictElement]:
    return {
        "access": DictElement(
            parameter_form=Dictionary(
                title=Title("Access to AWS API"),
                elements={
                    "global_service_region": DictElement(
                        parameter_form=SingleChoice(
                            title=Title("Use custom region for global AWS services"),
                            elements=[
                                SingleChoiceElement(
                                    title=Title("default (all normal AWS regions)"),
                                    name="default",
                                ),
                                *(
                                    SingleChoiceElement(
                                        title=Title(  # pylint: disable=localization-of-non-literal-string
                                            region
                                        ),
                                        name=region.replace("-", "_"),
                                    )
                                    for region in (
                                        "us-gov-east-1",
                                        "us-gov-west-1",
                                        "cn-north-1",
                                        "cn-northwest-1",
                                    )
                                ),
                            ],
                            prefill=DefaultValue("default"),
                        )
                    ),
                    "role_arn_id": DictElement(
                        parameter_form=Dictionary(
                            title=Title("Use STS AssumeRole to assume a different IAM role"),
                            elements={
                                "role_arn": DictElement(
                                    parameter_form=String(
                                        title=Title("The ARN of the IAM role to assume"),
                                        field_size=FieldSize.MEDIUM,
                                        help_text=Help(
                                            "The Amazon Resource Name (ARN) of the role to assume."
                                        ),
                                    ),
                                    required=True,
                                ),
                                "external_id": DictElement(
                                    parameter_form=String(
                                        title=Title("External ID (optional)"),
                                        field_size=FieldSize.MEDIUM,
                                        help_text=Help(
                                            "A unique identifier that might be required when you assume a role in another "
                                            "account. If the administrator of the account to which the role belongs provided "
                                            "you with an external ID, then provide that value in the External ID parameter. "
                                        ),
                                    ),
                                ),
                            },
                        )
                    ),
                },
            ),
            required=True,
        ),
    }


def _formspec_aws_piggyback_naming_convention() -> dict[str, DictElement]:
    return {
        "piggyback_naming_convention": DictElement(
            parameter_form=SingleChoice(
                title=Title("Piggyback names"),
                elements=[
                    SingleChoiceElement(
                        title=Title("IP - Region - Instance ID"),
                        name="ip_region_instance",
                    ),
                    SingleChoiceElement(
                        title=Title("Private IP DNS name"), name="private_dns_name"
                    ),
                ],
                help_text=Help(
                    "Each EC2 instance creates a piggyback host.<br><b>Note:</b> "
                    "Not every hostname is pingable and changing the piggyback name "
                    "will reset the piggyback host.<br><br><b>IP - Region - Instance "
                    'ID:</b><br>The name consists of "{Private IPv4 '
                    'address}-{Region}-{Instance ID}". This uniquely identifies the '
                    "EC2 instance. It is not possible to ping this host name."
                ),
                prefill=DefaultValue("ip_region_instance"),
            ),
            required=True,
        ),
    }


def _convert_regions(values: object) -> list[str]:
    if not isinstance(values, list):
        raise TypeError(values)
    return [region.replace("-", "_") for region in values]


def quick_setup_stage_1() -> Mapping[str, DictElement]:
    return {
        "access_key_id": DictElement(
            parameter_form=String(
                title=Title("The access key ID for your AWS account"),
                field_size=FieldSize.MEDIUM,
                custom_validate=(validators.LengthInRange(min_value=1),),
            ),
            required=True,
        ),
        "secret_access_key": DictElement(
            parameter_form=Password(
                title=Title("The secret access key for your AWS account"),
                custom_validate=(validators.LengthInRange(min_value=1),),
            ),
            required=True,
        ),
    }


def quick_setup_stage_2() -> Mapping[str, DictElement]:
    return {
        "regions_to_monitor": DictElement(
            parameter_form=MultipleChoice(
                title=Title("Regions to monitor"),
                elements=[
                    MultipleChoiceElement(
                        name=name.replace("-", "_"),
                        title=Title(title),  # pylint: disable=localization-of-non-literal-string
                    )
                    for name, title in aws_region_to_monitor()
                ],
            ),
            required=True,
        ),
    }


def quick_setup_stage_3() -> Mapping[str, DictElement]:
    valid_service_choices = {c.name for c in _regional_services()}
    return {
        "global_services": DictElement(
            parameter_form=MultipleChoice(
                title=Title("Global services to monitor"),
                elements=_global_services(),
                prefill=DefaultValue([]),
            ),
            required=True,
        ),
        "services": DictElement(
            parameter_form=MultipleChoice(
                title=Title("Services per region to monitor"),
                elements=_regional_services(),
                prefill=DefaultValue(list(valid_service_choices)),
            ),
            required=True,
        ),
    }


def quick_setup_advanced() -> Mapping[str, DictElement]:
    return {
        "proxy_details": DictElement(
            parameter_form=Dictionary(
                title=Title("Proxy server details"),
                elements={
                    "proxy_host": DictElement(
                        parameter_form=String(title=Title("Proxy host")),
                        required=True,
                    ),
                    "proxy_port": DictElement(
                        parameter_form=Integer(
                            title=Title("Port"),
                            custom_validate=[
                                validators.NumberInRange(
                                    0, 65535, Message("Port must be between 0 and 65535")
                                )
                            ],
                        )
                    ),
                    "proxy_user": DictElement(
                        parameter_form=String(title=Title("Username"), field_size=FieldSize.MEDIUM),
                    ),
                    "proxy_password": DictElement(
                        parameter_form=Password(
                            title=Title("Password"),
                        ),
                    ),
                },
            ),
        ),
        **_formspec_aws_api_access(),
        **_formspec_aws_piggyback_naming_convention(),
        "overall_tags": DictElement(
            parameter_form=formspec_aws_tags(
                Title("Restrict monitoring services by one of these AWS tags")
            ),
        ),
    }


def _formspec():
    return Dictionary(
        title=Title("Amazon Web Services (AWS)"),
        elements={
            **quick_setup_stage_1(),
            **quick_setup_stage_2(),
            **quick_setup_stage_3(),
            **quick_setup_advanced(),
        },
    )


# Add the form spec to the registry but don't register the rule spec.
form_spec_registry["aws"] = LoadedRuleSpec(
    rule_spec=SpecialAgent(
        name="aws",
        title=Title("Amazon Web Services (AWS)"),
        topic=Topic.CLOUD,
        parameter_form=_formspec,
    ),
    edition_only=Edition.CRE,
)
