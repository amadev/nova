# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
import mock

from nova import test
from nova.tests import fixtures as nova_fixtures
from nova.tests.unit.image import fake as fake_image
from nova.tests.unit import policy_fixture


keystone_projects = [
    {
        "description": "Bootstrap project for initializing the cloud.",
        "domain_id": "default",
        "enabled": True,
        "id": "019ce99cf9914edf8273ca663df5df7b",
        "is_domain": False,
        "links": {
            "self": ("http://fake_host/identity/"
                     "v3/projects/019ce99cf9914edf8273ca663df5df7b")
        },
        "name": "admin",
        "parent_id": "default"
    },
    {
        "description": "",
        "domain_id": "default",
        "enabled": True,
        "id": "6f70656e737461636b20342065766572",
        "is_domain": False,
        "links": {
            "self": ("http://fake_host/identity/"
                     "v3/projects/c57952b83d9b4507aa89cc32e5edeff6")
        },
        "name": "demo",
        "parent_id": "019ce99cf9914edf8273ca663df5df7b"
    },
    {
        "description": "",
        "domain_id": "default",
        "enabled": True,
        "id": "cdf5e93fae5841579546a402d0a647a8",
        "is_domain": False,
        "links": {
            "self": ("http://fake_host/identity/"
                     "v3/projects/cdf5e93fae5841579546a402d0a647a8")
        },
        "name": "invisible_to_admin",
        "parent_id": "default"
    }
]


class HierarchQuotasTestCase(test.TestCase):
    api_major_version = 'v2.1'

    def setUp(self):
        super(HierarchQuotasTestCase, self).setUp()
        fake_image.stub_out_image_service(self)
        self.useFixture(policy_fixture.RealPolicyFixture())
        self.useFixture(nova_fixtures.NoopConductorFixture())
        api_fixture = self.useFixture(nova_fixtures.OSAPIFixture(
            api_version='v2.1'))

        self.api = api_fixture.api
        self.api.microversion = 'latest'

    @mock.patch('keystoneclient.v3.projects.ProjectManager.list')
    def test_get_projects(self, projects_list):
        projects_list.return_value = [
            type('project', (object,), p) for p in keystone_projects]
        self.flags(quota_driver='nova.quota.HierarchyQuotaDriver')
        self.useFixture(nova_fixtures.AllServicesCurrent())
        image_ref = fake_image.get_valid_image_id()
        body = {
            'server': {
                'name': 'foo',
                'imageRef': image_ref,
                'flavorRef': '1',
                'networks': 'none',
            }
        }
        create_resp = self.api.api_post('servers', body)
        get_resp = self.api.api_get('servers/%s' %
                                    create_resp.body['server']['id'])

        server = get_resp.body['server']
        # Validate a few things
        self.assertEqual('foo', server['name'])
        self.assertEqual(image_ref, server['image']['id'])
        self.assertEqual('1', server['flavor']['id'])
        self.assertEqual('', server['hostId'])
        self.assertIsNone(None, server['OS-SRV-USG:launched_at'])
        self.assertIsNone(None, server['OS-SRV-USG:terminated_at'])
        self.assertFalse(server['locked'])
        self.assertEqual([], server['tags'])
        self.assertEqual('scheduling', server['OS-EXT-STS:task_state'])
        self.assertEqual('building', server['OS-EXT-STS:vm_state'])
        self.assertEqual('BUILD', server['status'])
