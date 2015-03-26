# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

import six

from st2common import log as logging
from st2common.constants.meta import ALLOWED_EXTS
from st2common.bootstrap.base import ResourceRegistrar
from st2common.models.api.rule import RuleAPI
from st2common.persistence.reactor import Rule
import st2common.content.utils as content_utils

__all__ = [
    'RulesRegistrar',
    'register_rules'
]

LOG = logging.getLogger(__name__)


class RulesRegistrar(ResourceRegistrar):
    ALLOWED_EXTENSIONS = ALLOWED_EXTS

    def register_rules_from_packs(self, base_dirs):
        """
        :return: Number of rules registered.
        :rtype: ``int``
        """
        registered_count = 0

        content = self._pack_loader.get_content(base_dirs=base_dirs,
                                                content_type='rules')
        for pack, rules_dir in six.iteritems(content):
            try:
                LOG.debug('Registering rules from pack: %s', pack)
                rules = self._get_rules_from_pack(rules_dir)
                count = self._register_rules_from_pack(pack, rules)
                registered_count += count
            except:
                LOG.exception('Failed registering all rules from pack: %s', rules_dir)

        return registered_count

    def register_rules_from_pack(self, pack_dir):
        """
        Register all the rules from the provided pack.

        :return: Number of rules registered.
        :rtype: ``int``
        """
        pack_dir = pack_dir[:-1] if pack_dir.endswith('/') else pack_dir
        _, pack = os.path.split(pack_dir)
        rules_dir = self._pack_loader.get_content_from_pack(pack_dir=pack_dir,
                                                            content_type='rules')

        registered_count = 0
        if not rules_dir:
            return registered_count

        LOG.debug('Registering rules from pack %s:, dir: %s', pack, rules_dir)

        try:
            rules = self._get_rules_from_pack(rules_dir=rules_dir)
            registered_count = self._register_rules_from_pack(pack=pack, rules=rules)
        except:
            LOG.exception('Failed registering all rules from pack: %s', rules_dir)

        return registered_count

    def _get_rules_from_pack(self, rules_dir):
        return self._get_resources_from_pack(resources_dir=rules_dir)

    def _register_rules_from_pack(self, pack, rules):
        registered_count = 0

        for rule in rules:
            LOG.debug('Loading rule from %s.', rule)
            try:
                content = self._meta_loader.load(rule)
                rule_api = RuleAPI(**content)
                rule_db = RuleAPI.to_model(rule_api)

                try:
                    rule_db.id = Rule.get_by_name(rule_api.name).id
                except ValueError:
                    LOG.debug('Rule %s not found. Creating new one.', rule)

                try:
                    rule_db = Rule.add_or_update(rule_db)
                    extra = {'rule_db': rule_db}
                    LOG.audit('Rule updated. Rule %s from %s.', rule_db, rule, extra=extra)
                except Exception:
                    LOG.exception('Failed to create rule %s.', rule_api.name)
            except:
                LOG.exception('Failed registering rule from %s.', rule)
            else:
                registered_count += 1

        return registered_count


def register_rules(packs_base_paths=None, pack_dir=None):
    if packs_base_paths:
        assert(isinstance(packs_base_paths, list))

    if not packs_base_paths:
        packs_base_paths = content_utils.get_packs_base_paths()

    registrar = RulesRegistrar()

    if pack_dir:
        result = registrar.register_rules_from_pack(pack_dir=pack_dir)
    else:
        result = registrar.register_rules_from_packs(base_dirs=packs_base_paths)

    return result
