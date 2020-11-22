# -*- coding: utf-8 -*-
"""
run tool dig on each in-scope second-level domain (e.g., megacorpone.com) using the operating system's DNS server to
obtain DNS resource records NS and CNAME. use optional argument --dns-server to explicitly specify another DNS server
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

import re
import logging
from typing import List
from collectors.os.modules.core import DomainCollector
from collectors.os.modules.dns.core import BaseDnsCollector
from collectors.os.modules.core import BaseCollector
from collectors.os.core import PopenCommand
from database.model import HostName
from database.model import Command
from database.model import CollectorName
from database.model import Source
from database.model import DnsResourceRecordType
from view.core import ReportItem
from sqlalchemy.orm.session import Session

logger = logging.getLogger('dnstakeover')


class CollectorClass(BaseDnsCollector, DomainCollector):
    """This class implements a collector module that is automatically incorporated into the application."""

    def __init__(self, **kwargs):
        super().__init__(priority=240,
                         timeout=0,
                         **kwargs)
        self._re_domain = re.compile("^\s*(?P<source_domain>[^;].+?)\s+[0-9]+\s+IN\s+"
                                     "(?P<type>(CNAME)|(NS))\s+(?P<destination_domain>.+?)$")
        self._resource_records = ["NS", "CNAME"]

    @staticmethod
    def get_argparse_arguments():
        return {"help": __doc__, "action": "store_true"}

    def create_domain_commands(self,
                               session: Session,
                               host_name: HostName,
                               collector_name: CollectorName) -> List[BaseCollector]:
        """This method creates and returns a list of commands based on the given service.

        This method determines whether the command exists already in the database. If it does, then it does nothing,
        else, it creates a new Collector entry in the database for each new command as well as it creates a corresponding
        operating system command and attaches it to the respective newly created Collector class.

        :param session: Sqlalchemy session that manages persistence operations for ORM-mapped objects
        :param host_name: The host name based on which commands shall be created.
        :param collector_name: The name of the collector as specified in table collector_name
        :return: List of Collector instances that shall be processed.
        """
        collectors = []
        if host_name:
            for item in self._resource_records:
                os_command = [self._path_dig,
                              '-t', item,
                              host_name.full_name]
                if self._dns_server:
                    os_command.append("@{}".format(self._dns_server))
                collector = self._get_or_create_command(session, os_command, collector_name, host_name=host_name)
                collectors.append(collector)
        return collectors

    def verify_results(self, session: Session,
                       command: Command,
                       source: Source,
                       report_item: ReportItem,
                       process: PopenCommand = None, **kwargs) -> None:
        """This method analyses the results of the command execution.

        After the execution, this method checks the OS command's results to determine the command's execution status as
        well as existing vulnerabilities (e.g. weak login credentials, NULL sessions, hidden Web folders). The
        stores the output in table command. In addition, the collector might add derived information to other tables as
        well.

        :param session: Sqlalchemy session that manages persistence operations for ORM-mapped objects
        :param command: The command instance that contains the results of the command execution
        :param source: The source object of the current collector
        :param report_item: Item that can be used for reporting potential findings in the UI
        :param process: The PopenCommand object that executed the given result. This object holds stderr, stdout, return
        code etc.
        """
        for line in command.stdout_output:
            match = self._re_domain.match(line)
            if match:
                type_str = match.group("type")
                if type_str:
                    type = DnsResourceRecordType[type_str.lower()]
                else:
                    type = None
                destination_domain = match.group("destination_domain")
                host_name = self.add_host_name(session=session,
                                               command=command,
                                               host_name=destination_domain,
                                               source=source,
                                               verify=True,
                                               report_item=report_item)
                if host_name:
                    self.add_host_name_host_name_mapping(session=session,
                                                         command=command,
                                                         source_host_name=command.host_name,
                                                         resolved_host_name=host_name,
                                                         source=source,
                                                         mapping_type=type,
                                                         report_item=report_item)
                else:
                    logger.debug("ignoring host name due to invalid domain in line: {}".format(line))
