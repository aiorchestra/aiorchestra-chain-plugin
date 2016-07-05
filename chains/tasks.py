#    Author: Denys Makogon
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import yaml

from aiorchestra.core import context
from aiorchestra.core import utils

DT = 'tosca.artifacts.chain.deployment_template'
DTI = 'tosca.artifacts.chain.deployment_inputs'
PC = 'tosca.artifacts.chain.persisted_context'


@utils.operation
async def create(node, inputs):
    node.context.logger.info('[{0}] - Building chain function '
                             'deployment context.'.format(node.name))
    template = node.get_artifact_from_type(DT)
    persisted_context = node.get_artifact_from_type(PC)
    if persisted_context and not template:
        raise Exception('[{0}] - Persisted context requires '
                        'template.'.format(node.name))
    if not template:
        raise Exception('[{0}] - Deployment template artifact '
                        'required.'.format(node.name))
    inputs = node.get_artifact_from_type(DTI)
    if not inputs:
        node.context.logger.warn('[{0}] - Inputs artifact was '
                                 'not specified.'.format(node.name))
    deployment_inputs_file = inputs.pop().get('file')
    deployment_template_file = template.pop().get('file')
    dti = {}
    if deployment_inputs_file:
        with open(deployment_inputs_file, 'r') as dti:
            dti = yaml.load(dti)
    deployment_context = context.OrchestraContext(
        node.name, path=deployment_template_file,
        template_inputs=dti, logger=node.context.logger,
        enable_rollback=node.context.rollback_enabled,
        event_loop=node.context.event_loop,
    )
    node.update_runtime_properties('deployment_context',
                                   deployment_context)
    node.context.logger.info('[{0}] - Deployment context assembled.'
                             .format(node.name))


@utils.operation
async def start(node, inputs):
    node.context.logger.info('[{0}] - Starting chain function '
                             'deployment.'.format(node.name))
    deployment_context = node.runtime_properties.get(
        'deployment_context')
    await deployment_context.deploy()
    outputs = deployment_context.outputs
    node.batch_update_runtime_properties(**{
        'deployment_context': deployment_context,
        'deployment_context_outputs': outputs,
        'persisted_context': deployment_context.serialize(),
    })
    node.context.logger.info('[{0}] - Deployment finished with '
                             'status "{1}".'
                             .format(node.name,
                                     deployment_context.
                                     status.upper()))


@utils.operation
async def stop(node, inputs):
    node.context.logger.info('[{0}] - Stopping chain function '
                             'deployment.'.format(node.name))
    deployment_context = node.runtime_properties.get(
        'deployment_context')
    await deployment_context.undeploy()
    node.context.logger.info('[{0}] - Deployment finished with '
                             'status "{1}".'
                             .format(node.name,
                                     deployment_context.
                                     status.upper()))


@utils.operation
async def delete(node, inputs):
    node.context.logger.info('[{0}] - Deleting chain function '
                             'deployment context.'.format(node.name))
    if 'deployment_context' in node.runtime_properties:
        del node.runtime_properties['deployment_context']
