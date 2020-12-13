# -*- coding: utf-8 -*-
"""
run tool changeme on each identified in-scope SSH service to test for default credentials and weak SSH keys
"""

__author__ = "Lukas Reiter"
__license__ = "GPL v3.0"
__copyright__ = """Copyright 2018 Lukas Reiter

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
__version__ = 0.1

import logging
from typing import List
from collectors.os.modules.core import ServiceCollector
from collectors.os.modules.core import BaseCollector
from collectors.os.modules.ssh.core import BaseSshChangeme
from collectors.os.modules.core import ChangeProtocol
from database.model import Service
from database.model import CollectorName
from sqlalchemy.orm.session import Session

logger = logging.getLogger('sshchangeme')


class CollectorClass(BaseSshChangeme, ServiceCollector):
    """This class implements a collector module that is automatically incorporated into the application."""

    def __init__(self, **kwargs):
        super().__init__(priority=11600,
                         timeout=0,
                         exec_user="kali",
                         **kwargs)

    @staticmethod
    def get_argparse_arguments():
        return {"help": __doc__, "action": "store_true"}

    def create_service_commands(self,
                                session: Session,
                                service: Service,
                                collector_name: CollectorName) -> List[BaseCollector]:
        """This method creates and returns a list of commands based on the given service.

        This method determines whether the command exists already in the database. If it does, then it does nothing,
        else, it creates a new Collector entry in the database for each new command as well as it creates a corresponding
        operating system command and attaches it to the respective newly created Collector class.

        :param session: Sqlalchemy session that manages persistence operations for ORM-mapped objects
        :param service: The service based on which commands shall be created.
        :param collector_name: The name of the collector as specified in table collector_name
        :return: List of Collector instances that shall be processed.
        """
        collectors = []
        if self.match_nmap_service_name(service):
            json_file = self.create_json_file_path(service=service)
            results = self._create_commands(session=session,
                                            service=service,
                                            collector_name=collector_name,
                                            protocol=ChangeProtocol.ssh,
                                            json_file=json_file,
                                            target="ssh://{}:{}".format(service.address, service.port))
            collectors.extend(results)
            json_file = self.create_json_file_path(service=service, create_new=True)
            results = self._create_commands(session=session,
                                            service=service,
                                            collector_name=collector_name,
                                            protocol=ChangeProtocol.ssh_key,
                                            json_file=json_file,
                                            target="ssh://{}:{}".format(service.address, service.port))
            collectors.extend(results)
        return collectors

