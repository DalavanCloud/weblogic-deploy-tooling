"""
Copyright (c) 2017, 2018, Oracle and/or its affiliates. All rights reserved.
The Universal Permissive License (UPL), Version 1.0
"""

from java.io import File
from java.lang import IllegalArgumentException

from oracle.weblogic.deploy.util import PyOrderedDict as OrderedDict
from oracle.weblogic.deploy.util import WLSDeployArchiveIOException

import oracle.weblogic.deploy.util.StringUtils as StringUtils
import wlsdeploy.aliases.model_constants as model_constants
import wlsdeploy.exception.exception_helper as exception_helper
import wlsdeploy.logging.platform_logger as platform_logger
import wlsdeploy.tool.discover.discoverer as discoverer
import wlsdeploy.util.wlst_helper as wlst_helper
from wlsdeploy.aliases.location_context import LocationContext
from wlsdeploy.aliases.wlst_modes import WlstModes
from wlsdeploy.tool.discover.coherence_resources_discoverer import CoherenceResourcesDiscoverer
from wlsdeploy.tool.discover.discoverer import Discoverer
from wlsdeploy.tool.discover.jms_resources_discoverer import JmsResourcesDiscoverer

_class_name = 'CommonResourcesDiscoverer'
_logger = platform_logger.PlatformLogger(discoverer.get_discover_logger_name())


class CommonResourcesDiscoverer(Discoverer):
    """
    Discover the weblogic resources that are common across global, resource group template, and
    partition resource group.
    """

    def __init__(self, model_context, resource_dictionary, wlst_mode=WlstModes.OFFLINE,
                 base_location=LocationContext()):
        """

        :param model_context: context about the model for this instance of discover domain
        :param resource_dictionary: to populate the common resources. By default, populates the initialized resources
        :param base_location: to look for common weblogic resources. By default this is the global path or '/'
        """
        Discoverer.__init__(self, model_context, wlst_mode, base_location)
        self._dictionary = resource_dictionary
        self._add_att_handler(model_constants.PATH_TO_SCRIPT, self._add_wldf_script)

    def discover(self):
        """
        Discover weblogic resources from the on-premise domain.
        :return: resources: dictionary where to populate discovered domain resources
        """
        _method_name = 'discover'
        _logger.entering(class_name=_class_name, method_name=_method_name)
        model_folder_name, folder_result = self.get_datasources()
        discoverer.add_to_model_if_not_empty(self._dictionary, model_folder_name, folder_result)
        model_folder_name, folder_result = self.get_foreign_jndi_providers()
        discoverer.add_to_model_if_not_empty(self._dictionary, model_folder_name, folder_result)
        model_folder_name, folder_result = self.get_mail_sessions()
        discoverer.add_to_model_if_not_empty(self._dictionary, model_folder_name, folder_result)
        model_folder_name, folder_result = self.get_file_stores()
        discoverer.add_to_model_if_not_empty(self._dictionary, model_folder_name, folder_result)
        model_folder_name, folder_result = self.get_jdbc_stores()
        discoverer.add_to_model_if_not_empty(self._dictionary, model_folder_name, folder_result)
        JmsResourcesDiscoverer(self._model_context, self._dictionary, wlst_mode=self._wlst_mode).discover()
        model_folder_name, folder_result = self.get_wldf_system_resources()
        discoverer.add_to_model_if_not_empty(self._dictionary, model_folder_name, folder_result)
        CoherenceResourcesDiscoverer(self._model_context, self._dictionary, wlst_mode=self._wlst_mode).discover()

        _logger.exiting(class_name=_class_name, method_name=_method_name)
        return self._dictionary

    def get_datasources(self):
        """
        Discover JDBC datasource information from the domain.
        :return: model name for the dictionary and the dictionary containing the datasources information
        """
        _method_name = 'get_datasources'
        _logger.entering(class_name=_class_name, method_name=_method_name)
        result = OrderedDict()
        model_top_folder_name = model_constants.JDBC_SYSTEM_RESOURCE
        model_second_folder = model_constants.JDBC_RESOURCE
        location = LocationContext(self._base_location)
        location.append_location(model_top_folder_name)
        datasources = self._find_names_in_folder(location)
        if datasources is not None:
            _logger.info('WLSDPLY-06340', len(datasources), class_name=_class_name, method_name=_method_name)
            name_token = self._alias_helper.get_name_token(location)
            for datasource in datasources:
                _logger.info('WLSDPLY-06341', datasource, class_name=_class_name, method_name=_method_name)
                result[datasource] = OrderedDict()
                location.add_name_token(name_token, datasource)
                self._populate_model_parameters(result[datasource], location)

                location.append_location(model_second_folder)
                wlst_helper.cd(self._alias_helper.get_wlst_attributes_path(location))
                result[datasource][model_second_folder] = OrderedDict()
                resource_result = result[datasource][model_second_folder]
                self._populate_model_parameters(resource_result, location)
                self._discover_subfolders(resource_result, location)
                location.remove_name_token(name_token)
                location.pop_location()
        _logger.exiting(class_name=_class_name, method_name=_method_name, result=result)
        return model_top_folder_name, result

    def get_foreign_jndi_providers(self):
        """
        Discover Foreign JNDI providers from the domain.
        :return: model name for the dictionary and the dictionary containing the foreign JNDI provider information
        """
        _method_name = 'get_foreign_jndi_providers'
        _logger.entering(class_name=_class_name, method_name=_method_name)
        result = OrderedDict()
        model_top_folder_name = model_constants.FOREIGN_JNDI_PROVIDER
        location = LocationContext(self._base_location)
        location.append_location(model_top_folder_name)
        providers = self._find_names_in_folder(location)
        if providers is not None:
            _logger.info('WLSDPLY-06342', len(providers), class_name=_class_name, method_name=_method_name)
            name_token = self._alias_helper.get_name_token(location)
            for provider in providers:
                _logger.info('WLSDPLY-06343', provider, class_name=_class_name, method_name=_method_name)
                location.add_name_token(name_token, provider)
                result[provider] = OrderedDict()
                self._populate_model_parameters(result[provider], location)
                self._discover_subfolders(result[provider], location)
                location.remove_name_token(name_token)
        _logger.exiting(class_name=_class_name, method_name=_method_name, result=model_top_folder_name)
        return model_top_folder_name, result

    def get_mail_sessions(self):
        """
        Discover the mail sessions from the domain.
        :return: model name for the dictionary and the dictionary containing the mail session information
        """
        _method_name = 'get_mail_sessions'
        _logger.entering(class_name=_class_name, method_name=_method_name)
        result = OrderedDict()
        model_top_folder_name = model_constants.MAIL_SESSION
        location = LocationContext(self._base_location)
        location.append_location(model_top_folder_name)
        mail_sessions = self._find_names_in_folder(location)
        if mail_sessions is not None:
            _logger.info('WLSDPLY-06344', len(mail_sessions), class_name=_class_name, method_name=_method_name)
            name_token = self._alias_helper.get_name_token(location)
            for mail_session in mail_sessions:
                _logger.info('WLSDPLY-06345', mail_session, class_name=_class_name, method_name=_method_name)
                result[mail_session] = OrderedDict()
                mail_session_result = result[mail_session]
                location.add_name_token(name_token, mail_session)
                self._populate_model_parameters(mail_session_result, location)
                _fix_passwords_in_properties(mail_session_result)
                location.remove_name_token(name_token)

        _logger.exiting(class_name=_class_name, method_name=_method_name, result=model_top_folder_name)
        return model_top_folder_name, result

    def get_file_stores(self):
        """
        Discover the file stores used for weblogic persistence
        :return: model folder name: dictionary with the discovered file stores
        """
        _method_name = 'get_file_stores'
        _logger.entering(class_name=_class_name, method_name=_method_name)
        result = OrderedDict()
        model_top_folder_name = model_constants.FILE_STORE
        location = LocationContext(self._base_location)
        location.append_location(model_top_folder_name)
        file_stores = self._find_names_in_folder(location)
        if file_stores is not None:
            _logger.info('WLSDPLY-06346', len(file_stores), class_name=_class_name, method_name=_method_name)
            name_token = self._alias_helper.get_name_token(location)
            for file_store in file_stores:
                _logger.info('WLSDPLY-06347', file_store, class_name=_class_name, method_name=_method_name)
                result[file_store] = OrderedDict()
                location.add_name_token(name_token, file_store)
                self._populate_model_parameters(result[file_store], location)
                self.archive_file_store_directory(file_store, result[file_store])
                location.remove_name_token(name_token)
        _logger.exiting(class_name=_class_name, method_name=_method_name, result=result)
        return model_top_folder_name, result

    def archive_file_store_directory(self, file_store_name, file_store_dictionary):
        _method_name = 'archive_file_store_directory'
        _logger.entering(file_store_name, class_name=_class_name, method_name=_method_name)
        if file_store_name is not None and model_constants.DIRECTORY in file_store_dictionary:
            directory = file_store_dictionary[model_constants.DIRECTORY]
            if not StringUtils.isEmpty(directory):
                archive_file = self._model_context.get_archive_file()
                try:
                    new_source_name = archive_file.addFileStoreDirectory(file_store_name)
                except WLSDeployArchiveIOException, wioe:
                    de = exception_helper.create_discover_exception('WLSDPLY-06348', file_store_name, directory,
                                                                    wioe.getLocalizedMessage())
                    _logger.throwing(class_name=_class_name, method_name=_method_name, error=de)
                    raise de
                if new_source_name is not None:
                    _logger.info('WLSDPLY-06349', file_store_name, new_source_name, class_name=_class_name,
                                 method_name=_method_name)
                    file_store_dictionary[model_constants.DIRECTORY] = new_source_name

        _logger.exiting(class_name=_class_name, method_name=_method_name)
        return

    def get_jdbc_stores(self):
        """
        Discover the JDBC stores used for weblogic persistence
        :return: model file name: dictionary containing discovered JDBC stores
        """
        _method_name = 'get_jdbc_stores'
        _logger.entering(class_name=_class_name, method_name=_method_name)
        result = OrderedDict()
        model_top_folder_name = model_constants.JDBC_STORE
        location = LocationContext(self._base_location)
        location.append_location(model_top_folder_name)
        jdbc_stores = self._find_names_in_folder(location)
        if jdbc_stores is not None:
            _logger.info('WLSDPLY-06350', len(jdbc_stores), class_name=_class_name, method_name=_method_name)
            name_token = self._alias_helper.get_name_token(location)
            for jdbc_store in jdbc_stores:
                _logger.info('WLSDPLY-06351', jdbc_store, class_name=_class_name, method_name=_method_name)
                result[jdbc_store] = OrderedDict()
                location.add_name_token(name_token, jdbc_store)
                self._populate_model_parameters(result[jdbc_store], location)
                self.archive_jdbc_create_script(jdbc_store, result[jdbc_store])
                location.remove_name_token(name_token)
        _logger.exiting(class_name=_class_name, method_name=_method_name, result=result)
        return model_top_folder_name, result

    def archive_jdbc_create_script(self, jdbc_store_name, jdbc_store_dictionary):
        """
        Add the JDBC store create DDL file to the archive.
        :param jdbc_store_name: name of the JDBC Store
        :param jdbc_store_dictionary: dictionary containing the discovered store attributes
        """
        _method_name = 'get_jdbc_create_script'
        _logger.entering(jdbc_store_name, class_name=_class_name, method_name=_method_name)
        if model_constants.CREATE_TABLE_DDL_FILE in jdbc_store_dictionary:
            archive_file = self._model_context.get_archive_file()
            file_name = jdbc_store_dictionary[model_constants.CREATE_TABLE_DDL_FILE]
            _logger.info('WLSDPLY-06352', jdbc_store_name, file_name, class_name=_class_name, method_name=_method_name)
            try:
                new_source_name = archive_file.addScript(File(file_name))
            except IllegalArgumentException, iae:
                _logger.warning('WLSDPLY-06353', jdbc_store_name, file_name,
                                iae.getLocalizedMessage(), class_name=_class_name,
                                method_name=_method_name)
                _logger.exiting(class_name=_class_name, method_name=_method_name)
                return
            except WLSDeployArchiveIOException, wioe:
                de = exception_helper.create_discover_exception('WLSDPLY-06354', jdbc_store_name, file_name,
                                                                wioe.getLocalizedMessage())
                _logger.throwing(class_name=_class_name, method_name=_method_name, error=de)
                raise de

            if new_source_name is None:
                new_source_name = file_name
            tokenized = self._model_context.tokenize_path(new_source_name)
            jdbc_store_dictionary[model_constants.CREATE_TABLE_DDL_FILE] = tokenized

        _logger.exiting(class_name=_class_name, method_name=_method_name)
        return

    def get_path_services(self):
        """
        Discover the path services for weblogic message grouping.
        :return: model file name: dictionary containing discovered path services
        """
        _method_name = 'get_path_services'
        _logger.entering(class_name=_class_name, method_name=_method_name)
        result = OrderedDict()
        model_top_folder_name = model_constants.PATH_SERVICE
        location = LocationContext(self._base_location)
        location.append_location(model_top_folder_name)
        path_services = self._find_names_in_folder(location)
        if path_services is not None:
            _logger.info('WLSDPLY-06355', len(path_services), class_name=_class_name, method_name=_method_name)
            name_token = self._alias_helper.get_name_token(location)
            for path_service in path_services:
                _logger.info('WLSDPLY-06356', path_service, class_name=_class_name, method_name=_method_name)
                result[path_service] = OrderedDict()
                location.add_name_token(name_token, path_service)
                self._populate_model_parameters(result[path_service], location)
                location.remove_name_token(name_token.PATHSERVICE)
        _logger.exiting(class_name=_class_name, method_name=_method_name, result=result)
        return model_top_folder_name, result

    def get_wldf_system_resources(self):
        """
        Discover each WLDF system resource in the domain.
        :return: model name for the WLDF system resource:dictionary containing the discovered WLDF system resources
        """
        _method_name = 'get_wldf_system_resources'
        _logger.entering(class_name=_class_name, method_name=_method_name)
        result = OrderedDict()
        model_top_folder_name = model_constants.WLDF_SYSTEM_RESOURCE
        location = LocationContext(self._base_location)
        location.append_location(model_top_folder_name)
        wldf_resources = self._find_names_in_folder(location)
        if wldf_resources is not None:
            _logger.info('WLSDPLY-06357', len(wldf_resources), class_name=_class_name, method_name=_method_name)
            name_token = self._alias_helper.get_name_token(location)
            for wldf_resource in wldf_resources:
                _logger.info('WLSDPLY-06358', wldf_resource, class_name=_class_name, method_name=_method_name)
                location.add_name_token(name_token, wldf_resource)
                result[wldf_resource] = OrderedDict()
                self._populate_model_parameters(result[wldf_resource], location)
                self._discover_subfolders(result[wldf_resource], location)
                location.remove_name_token(name_token)
        _logger.exiting(class_name=_class_name, method_name=_method_name, result=model_top_folder_name)
        return model_top_folder_name, result

    # private methods

    def _add_wldf_script(self, model_name, model_value, location):
        """
        Add the WLDF WatchNotification ScriptAction script for attribute PathToScript to the archive file.
        Modify the model_value to reflect the new name after the archive file has been deployed.
        :param model_name: name of the  attribute
        :param model_value: containing the Script Action script
        :param location: context containing the current location of the ScriptAction
        :return: modified model value reflecting new PathToScript location
        """
        _method_name = '_add_wldf_script'
        _logger.entering(model_name, class_name=_class_name, method_name=_method_name)
        new_script_name = model_value
        if model_value is not None:
            _logger.info('WLSDPLY-06359', model_value, self.get_context(location), class_name=_class_name,
                         method_name=_method_name)
            archive_file = self._model_context.get_archive_file()
            # Set model_value to None if unable to add it to archive file
            modified_name = None
            try:
                modified_name = archive_file.addScript(File(model_value))
            except IllegalArgumentException, iae:
                _logger.warning('WLSDPLY-06360', self.get_context(location), model_value,
                                iae.getLocalizedMessage(), class_name=_class_name,
                                method_name=_method_name)
            except WLSDeployArchiveIOException, wioe:
                de = exception_helper.create_discover_exception('WLSDPLY-06354', self.get_context(location),
                                                                model_value, wioe.getLocalizedMessage())
                _logger.throwing(class_name=_class_name, method_name=_method_name, error=de)
                raise de
            new_script_name = modified_name
        _logger.exiting(class_name=_class_name, method_name=_method_name, result=new_script_name)
        return new_script_name


def _fix_passwords_in_properties(dictionary):
    """
    Look for password properties in the mail session properties string, and replace the password with a fix me token.
    :param dictionary: containing the discovered mail session attributes
    """
    match_pattern = "mail\.\w*\.?password"
    replacement = '--FIX ME--'
    if model_constants.MAIL_SESSION_PROPERTIES in dictionary:
        new_properties = ''
        string_properties = dictionary[model_constants.MAIL_SESSION_PROPERTIES]
        if string_properties:
            properties = string_properties
            if isinstance(string_properties, str):
                properties = StringUtils.formatPropertiesFromString(string_properties)
            new_properties = OrderedDict()
            iterator = properties.stringPropertyNames().iterator()
            while iterator.hasNext():
                key = iterator.next()
                new_key = str(key).strip()
                value = properties.getProperty(key)
                if StringUtils.matches(match_pattern, new_key):
                    value = replacement
                new_properties[new_key] = value
        dictionary[model_constants.MAIL_SESSION_PROPERTIES] = new_properties