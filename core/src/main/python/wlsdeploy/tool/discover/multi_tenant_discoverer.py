"""
Copyright (c) 2017, 2018, Oracle and/or its affiliates. All rights reserved.
The Universal Permissive License (UPL), Version 1.0
"""

import oracle.weblogic.deploy.util.PyOrderedDict as OrderedDict

import wlsdeploy.aliases.model_constants as model_constants
import wlsdeploy.tool.discover.discoverer as discoverer
from wlsdeploy.aliases.location_context import LocationContext
from wlsdeploy.aliases.wlst_modes import WlstModes
from wlsdeploy.logging.platform_logger import PlatformLogger
from wlsdeploy.tool.discover.common_resources_discoverer import CommonResourcesDiscoverer
from wlsdeploy.tool.discover.deployments_discoverer import DeploymentsDiscoverer
from wlsdeploy.tool.discover.discoverer import Discoverer
from wlsdeploy.tool.discover.multi_tenant_resources_discoverer import MultiTenantResourcesDiscoverer
from wlsdeploy.tool.discover.multi_tenant_topology_discoverer import MultiTenantTopologyDiscoverer

_class_name = 'MultiTenantDiscoverer'
_logger = PlatformLogger(discoverer.get_discover_logger_name())


class MultiTenantDiscoverer(Discoverer):
    """
    Discover the weblogic multi-tenant domain. Discover the topology components and resource components that are used
    for multi-tenant. Discover the resource group templates and the global resource groups. Discover the
    partition resources and deployments, including partition resource groups.
    """

    def __init__(self, model, model_context, wlst_mode=WlstModes.OFFLINE):
        Discoverer.__init__(self, model_context, wlst_mode)
        self._model = model

    def discover(self):
        _method_name = 'discover'
        _logger.entering(class_name=_class_name, method_name=_method_name)
        _logger.info('WLSDPLY-06700', class_name=_class_name, method_name=_method_name)
        MultiTenantTopologyDiscoverer(self._model_context, self._model.get_model_topology(),
                                      wlst_mode=self._wlst_mode).discover()
        MultiTenantResourcesDiscoverer(self._model_context, self._model.get_model_resources(),
                                       wlst_mode=self._wlst_mode).discover()
        dictionary = self._model.get_model_resources()
        model_folder_name, result = self.get_resource_group_templates()
        discoverer.add_to_model_if_not_empty(dictionary, model_folder_name, result)
        model_folder_name, result = self.get_resource_groups(self._base_location)
        discoverer.add_to_model_if_not_empty(dictionary, model_folder_name, result)
        model_folder_name, result = self.get_partitions()
        discoverer.add_to_model_if_not_empty(dictionary, model_folder_name, result)
        _logger.exiting(class_name=_class_name, method_name=_method_name)
        return self._model.get_model()

    def get_resource_group_templates(self):
        """
        Discover the resource group templates used by one to many partitions. Discover the resources that
        are contained by the resource group template.
        :return: model name for template:dictionary containing discovered resource group templates
        """
        _method_name = 'get_resource_group_templates'
        _logger.entering(class_name=_class_name, method_name=_method_name)
        result = OrderedDict()
        model_top_folder_name = model_constants.RESOURCE_GROUP_TEMPLATE
        location = LocationContext(self._base_location)
        location.append_location(model_top_folder_name)
        templates = self._find_names_in_folder(location)
        if templates is not None:
            _logger.info('WLSDPLY-06701', len(templates), class_name=_class_name, method_name=_method_name)
            name_token = self._alias_helper.get_name_token(location)
            for template in templates:
                _logger.info('WLSDPLY-06702', template, class_name=_class_name, method_name=_method_name)
                location.add_name_token(name_token, template)
                result[template] = self._discover_single_folder(location)
                CommonResourcesDiscoverer(self._model_context, result[template],
                                          wlst_mode=self._wlst_mode, base_location=location).discover()
                DeploymentsDiscoverer(self._model_context, result[template],
                                      wlst_mode=self._wlst_mode, base_location=location).discover()
                location.remove_name_token(name_token)
        _logger.exiting(class_name=_class_name, method_name=_method_name, result=model_top_folder_name)
        return model_top_folder_name, result

    def get_resource_groups(self, base_location):
        """
        Discover the resource groups located at the indicated base_location - global or partition.
        :param base_location: context containing the current location information
        :return: model name for dictionary:dictionary containing the discovered resource groups
        """
        _method_name = 'get_resource_groups'
        _logger.entering(str(base_location), class_name=_class_name, method_name=_method_name)
        result = OrderedDict()
        model_top_folder_name = model_constants.RESOURCE_GROUP
        location = LocationContext(base_location)
        location.append_location(model_top_folder_name)
        resource_groups = self._find_names_in_folder(location)
        if resource_groups is not None:
            _logger.info('WLSDPLY-06703', len(resource_groups), class_name=_class_name, method_name=_method_name)
            name_token = self._alias_helper.get_name_token(location)
            for resource_group in resource_groups:
                _logger.info('WLSDPLY-06704', resource_group, self.get_context(location), class_name=_class_name,
                             method_name=_method_name)
                location.add_name_token(name_token, resource_group)
                result[resource_group] = self._discover_single_folder(location)
                CommonResourcesDiscoverer(self._model_context, result[resource_group],
                                          wlst_mode=self._wlst_mode, base_location=location).discover()
                DeploymentsDiscoverer(self._model_context, result[resource_group],
                                      wlst_mode=self._wlst_mode, base_location=location).discover()
                location.remove_name_token(name_token)
        _logger.exiting(class_name=_class_name, method_name=_method_name, result=model_top_folder_name)
        return model_top_folder_name, result

    def get_partitions(self):
        """
        Discover the partitions for the domain, including partition resources and resource groups.
        :return: model name for the dictionary:dictionary containing the discovered partitions
        """
        _method_name = 'get_partitions'
        _logger.entering(class_name=_class_name, method_name=_method_name)
        result = OrderedDict()
        model_top_folder_name = model_constants.PARTITION
        location = LocationContext(self._base_location)
        location.append_location(model_top_folder_name)
        partitions = self._find_names_in_folder(location)
        if partitions is not None:
            _logger.info('WLSDPLY-06705', len(partitions), class_name=_class_name, method_name=_method_name)
            name_token = self._alias_helper.get_name_token(location)
            for partition in partitions:
                _logger.info('WLSDPLY-06706', partition, class_name=_class_name, method_name=_method_name)
                location.add_name_token(name_token, partition)
                result[partition] = self._discover_single_folder(location)
                model_rg_name, rg_result = self.get_resource_groups(location)
                discoverer.add_to_model_if_not_empty(result[partition], model_rg_name, rg_result)
                wlst_subfolders = self._find_subfolders(location)
                if wlst_subfolders is not None:
                    for wlst_subfolder in wlst_subfolders:
                        model_subfolder_name = self._get_model_name(location, wlst_subfolder)
                        if model_subfolder_name and not model_subfolder_name == model_constants.RESOURCE_GROUP:
                            self._discover_subfolder(model_subfolder_name, location, result[partition])
                location.remove_name_token(name_token)
        _logger.exiting(class_name=_class_name, method_name=_method_name, result=model_top_folder_name)
        return model_top_folder_name, result