"""
Copyright (c) 2017, 2018, Oracle and/or its affiliates. All rights reserved.
The Universal Permissive License (UPL), Version 1.0
"""

import os

from java.lang import StringBuilder

from oracle.weblogic.deploy.aliases import AliasException
from oracle.weblogic.deploy.util import PyOrderedDict as OrderedDict
from oracle.weblogic.deploy.util import PyWLSTException

import oracle.weblogic.deploy.util.StringUtils as StringUtils
import wlsdeploy.exception.exception_helper as exception_helper
import wlsdeploy.logging.platform_logger as platform_logger
import wlsdeploy.util.path_utils as path_utils
import wlsdeploy.util.wlst_helper as wlst_helper
from wlsdeploy.aliases.aliases import Aliases
from wlsdeploy.aliases.location_context import LocationContext
from wlsdeploy.aliases.wlst_modes import WlstModes
from wlsdeploy.exception.expection_types import ExceptionType
from wlsdeploy.tool.util.alias_helper import AliasHelper
from wlsdeploy.tool.util.wlst_helper import WlstHelper
from wlsdeploy.util.weblogic_helper import WebLogicHelper

_DISCOVER_LOGGER_NAME = 'wlsdeploy.discover'

_class_name = 'Discoverer'
_logger = platform_logger.PlatformLogger(_DISCOVER_LOGGER_NAME)


class Discoverer(object):
    """
    Discoverer contains the private methods used to facilitate discovery of the domain information by its subclasses.
    """

    def __init__(self, model_context, wlst_mode, base_location=LocationContext()):
        """

        :param model_context: context about the model for this instance of discover domain
        :param base_location: to look for common weblogic resources. By default this is the global path or '/'
        """
        self._model_context = model_context
        self._base_location = base_location
        self._wlst_mode = wlst_mode
        self.__aliases = Aliases(self._model_context, wlst_mode=self._wlst_mode)
        self._alias_helper = AliasHelper(self.__aliases, _logger, ExceptionType.DISCOVER)
        self._att_handler_map = OrderedDict()
        self._wls_version = WebLogicHelper(_logger).get_actual_weblogic_version()
        self._wlst_helper = WlstHelper(_logger, ExceptionType.DISCOVER)

    def get_context(self, location):
        """
        Get current contextual information about what is currently being discovered and return as a descriptive string.
        :param location: context containing the current location information
        :return: string description constructed from the location context
        """
        descrip = StringBuilder()
        contexts = location.get_model_folders()
        before = ''
        context_location = LocationContext()
        if contexts is not None:
            for context in contexts:
                descrip.append(before).append(context)
                before = ' '
                context_location.append_location(context)
                token = self._alias_helper.get_name_token(context_location)
                if token is not None:
                    name = location.get_name_for_token(token)
                    if name is not None:
                        descrip.append(before).append(name)
        return descrip.toString()

    # methods for use only by the subclasses

    def _populate_model_parameters(self, dictionary, location):
        """
        Populate the model dictionary with the attribute values discovered at the current location. Perform
        any special processing for a specific attribute before storing into the model dictionary.
        :param dictionary: where to store the discovered attributes
        :param location: context containing current location information
        :return: dictionary of model attribute name and wlst value
        """
        _method_name = '_populate_model_parameters'
        wlst_path = self._alias_helper.get_wlst_attributes_path(location)
        _logger.finer('WLSDPLY-06100', wlst_path, class_name=_class_name, method_name=_method_name)
        self._wlst_helper.cd(wlst_path)
        wlst_params = self._wlst_helper.lsa()
        _logger.finest('WLSDPLY-06102', self._wlst_helper.get_pwd(), wlst_params, class_name=_class_name,
                       method_name=_method_name)
        wlst_get_params = self._alias_helper.get_wlst_get_required_attribute_names(location)
        _logger.finest('WLSDPLY-06103', str(location), wlst_get_params,
                       class_name=_class_name, method_name=_method_name)
        attr_dict = OrderedDict()
        if wlst_params:
            for wlst_param in wlst_params:
                if wlst_param in wlst_get_params:
                    _logger.finest('WLSDPLY-06104', wlst_param, class_name=_class_name, method_name=_method_name)
                    wlst_value = self._wlst_helper.get(wlst_param)
                else:
                    wlst_value = wlst_params[wlst_param]
                _logger.finest('WLSDPLY-06105', wlst_param, wlst_value, wlst_path, class_name=_class_name,
                               method_name=_method_name)
                try:
                    model_param, model_value = self.__aliases.get_model_attribute_name_and_value(location, wlst_param,
                                                                                                 wlst_value)
                except AliasException, ae:
                    _logger.warning('WLSDPLY-06106', wlst_param, self.get_context(location),
                                    self._get_wlst_mode_string(), self._wls_version, ae.getLocalizedMessage(),
                                    class_name=_class_name, method_name=_method_name)
                    continue

                attr_dict[model_param] = wlst_value
                model_value = self._check_attribute(model_param, model_value, location)
                if model_value is not None:
                    _logger.finer('WLSDPLY-06107', model_param, model_value, class_name=_class_name,
                                  method_name=_method_name)
                    dictionary[model_param] = model_value
                elif model_param is None:
                    _logger.finest('WLSDPLY-06108', model_param, class_name=_class_name, method_name=_method_name)
        return attr_dict

    def _get_attributes_for_current_location(self, location):
        """
        Change to the mbean folder with the provided name using the current location and return
        the attributes at that location.
        :param location: context with the current location information
        :return: list of attributes
        """
        _method_name = '_get_attributes_for_current_location'
        attributes = None
        path = self._alias_helper.get_wlst_attributes_path(location)
        try:
            attributes = wlst_helper.lsa(path)
        except PyWLSTException, pe:
            name = location.get_model_folders()[-1]
            _logger.fine('WLSDPLY-06109', name, str(location), pe.getLocalizedMessage(), class_name=_class_name,
                         method_name=_method_name)
        return attributes

    def _check_attribute(self, model_name, model_value, location):
        """
        Check to see if the attribute has special handling indicated by the discover handler map. If the
        attribute needs special processing, all the handler specified by the map.
        :param model_name: model name for the attribute to check
        :param model_value: value converted to model format
        :param location: context containing current location information
        :return: new value if modified by the handler or the original value if not a special attribute
        """
        new_value = model_value
        if model_name in self._att_handler_map:
            type_method = self._att_handler_map[model_name]
            if type_method is not None:
                new_value = type_method(model_name, model_value, location)
        return new_value

    def _find_names_in_folder(self, location):
        """
        Find the names for the top folder in the current location.
        :param location: context containing the current location information
        :return: list of names for the folder or None if the folder does not exist in the domain
        """
        _method_name = '_find_names_in_folder'
        names = None
        mbean_type = self._alias_helper.get_wlst_mbean_type(location)
        if mbean_type is None:
            _logger.fine('WLSDPLY-06110', location.get_model_folders()[-1], self._get_wlst_mode_string(),
                         self._wls_version, class_name=_class_name, method_name=_method_name)
        else:
            folder_path = self._alias_helper.get_wlst_list_path(location)
            _logger.finest('WLSDPLY-06111', folder_path, class_name=_class_name, method_name=_method_name)
            if wlst_helper.path_exists(folder_path):
                self._wlst_helper.cd(folder_path)
                names = self._wlst_helper.lsc()
        return names

    def _find_singleton_name_in_folder(self, location):
        """
        The top folder is a singleton. Find the single name for the folder.
        :param location: context containing current location informationget_mbean_folders
        :return: The single name for the folder, or None if the top folder does not exist in the domain
        """
        _method_name = '_find_singleton_name_in_top_folder'
        name = None
        names = self._find_names_in_folder(location)
        if names is not None:
            names_len = len(names)
            if names_len > 1:
                ex = exception_helper.create_discover_exception('WLSDPLY-06112', location.get_model_folders(),
                                                                self.get_context(location), len(names))
                _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
                raise ex
            if names_len > 0:
                name = names[0]
        return name

    def _find_subfolders(self, location):
        """
        Find the subfolders of the current location.
        :param location: context containing current location information
        :return: list of subfolders
        """
        wlst_path = self._alias_helper.get_wlst_subfolders_path(location)
        self._wlst_helper.cd(wlst_path)
        wlst_subfolders = self._wlst_helper.lsc()
        if len(wlst_subfolders) == 0:
            wlst_subfolders = None
        return wlst_subfolders

    def _discover_subfolder_singleton(self, model_subfolder_name, location):
        """
        Discover the subfolder from the wlst subfolder name. populate the attributes in the folder.
        Return the subfolder model name and  the dictionary populated from the subfolder.
        The location is appended and then removed from the provided location context prior to return.
        :param model_subfolder_name: subfolder name in wlst format
        :param location: containing the current location information
        :return: model subfolder name: subfolder result dictionary:
        """
        _method_name = '_discover_subfolder_singleton'
        _logger.entering(model_subfolder_name, str(location), class_name=_class_name, method_name=_method_name)
        subfolder_result = OrderedDict()
        # For all server subfolder names there should only be one path
        subfolder_path = self._alias_helper.get_wlst_attributes_path(location)
        self._wlst_helper.cd(subfolder_path)
        self._populate_model_parameters(subfolder_result, location)
        self._discover_subfolders(subfolder_result, location)
        _logger.finest('WLSDPLY-06113', str(location), class_name=_class_name, method_name=_method_name)
        _logger.exiting(class_name=_class_name, method_name=_method_name)
        return subfolder_result

    def _discover_subfolder_with_single_name(self, model_subfolder_name, location, name_token):
        """
        Discover a subfolder that is a singleton but has an unpredictable naming strategy. Find the name for
        the singleton folder and then discover the folder contents.
        :param location: context containing current location information
        :param name_token: represents the single folder name token in the aliases
        :return: dictionary containing discovered folder attributes
        """
        _method_name = '_discover_subfolder_with_single_name'
        _logger.entering(name_token, class_name=_class_name, method_name=_method_name)
        name = self._find_singleton_name_in_folder(location)
        result = OrderedDict()
        if name:
            location.add_name_token(name_token, name)
            result = self._discover_subfolder_singleton(model_subfolder_name, location)
            location.remove_name_token(name_token)
        _logger.exiting(class_name=_class_name, method_name=_method_name)
        return result

    def _discover_subfolder_with_names(self, model_subfolder_name, location, name_token):
        """
        Discover the subfolders from the wlst subfolder name. The subfolder may contain 0 to n instances, each
        with a unique name. Create an entry for each name in the subfolder. Populate the attributes of the subfolder.
        Return the subfolder model name and the populated dictionary.
        :param model_subfolder_name: model name of the wlst subfolder
        :param location: context of the current location
        :param name_token: aliases token for the type of model folder name
        :return: model subfolder name: dictionary results:
        """
        _method_name = '_discover_subfolder_with_names'
        _logger.entering(model_subfolder_name, str(location), name_token, class_name=_class_name,
                         method_name=_method_name)
        subfolder_result = OrderedDict()
        names = self._find_names_in_folder(location)
        if names is not None:
            for name in names:
                _logger.finer('WLSDPLY-06113', name, self.get_context(location),
                              class_name=_class_name, method_name=_method_name)
                subfolder_result[name] = OrderedDict()
                location.add_name_token(name_token, name)
                subfolder_path = self._alias_helper.get_wlst_attributes_path(location)
                self._wlst_helper.cd(subfolder_path)
                self._populate_model_parameters(subfolder_result[name], location)
                self._discover_subfolders(subfolder_result[name], location)
                location.remove_name_token(name_token)
        _logger.finest('WLSDPLY-06114', str(location), class_name=_class_name, method_name=_method_name)
        _logger.exiting(class_name=_class_name, method_name=_method_name)
        return subfolder_result

    def _discover_subfolder(self, model_subfolder_name, location, result=None):
        """
        Discover the subfolder indicated by the model subfolder name. Append the model subfolder to the
        current location context, and pop that location before return
        :param result: dictionary to store the discovered information
        :param location: context containing the current subfolder information
        :return: discovered dictionary
        """
        _method_name = '_discover_subfolder'
        _logger.entering(model_subfolder_name, class_name=_class_name, method_name=_method_name)
        location.append_location(model_subfolder_name)
        _logger.finer('WLSDPLY-06115', model_subfolder_name, self.get_context(location), class_name=_class_name,
                      method_name=_method_name)
        # handle null model_subfolder name which should never happen in discover. throw exception about version
        if result is None:
            result = OrderedDict()
        name_token = self._alias_helper.get_name_token(location)
        _logger.finest('WLSDPLY-06116', model_subfolder_name, self.get_context(location), name_token,
                       class_name=_class_name, method_name=_method_name)
        if name_token is not None:
            if self._alias_helper.requires_unpredictable_single_name_handling(location):
                subfolder_result = self._discover_subfolder_with_single_name(model_subfolder_name, location,
                                                                             name_token)
            else:
                subfolder_result = self._discover_subfolder_with_names(model_subfolder_name, location,
                                                                       name_token)
        else:
            subfolder_result = self._discover_subfolder_singleton(model_subfolder_name, location)
        add_to_model_if_not_empty(result, model_subfolder_name, subfolder_result)
        location.pop_location()
        _logger.exiting(class_name=_class_name, method_name=_method_name, result=result)
        return result

    def _discover_subfolders(self, result, location):
        """
        Discover the rest of the mbean hierarchy at the current location.
        :param result: dictionary where to store the discovered subfolders
        :param location: context containing current location information
        :return: populated dictionary
        """
        _method_name = '_discover_subfolders'
        _logger.entering(str(location), method_name=_method_name, class_name=_class_name)
        wlst_subfolders = self._find_subfolders(location)
        if wlst_subfolders is not None:
            for wlst_subfolder in wlst_subfolders:
                model_subfolder_name = self._get_model_name(location, wlst_subfolder)
                # will return a None if subfolder not in current wls version
                if model_subfolder_name is not None:
                    result = self._discover_subfolder(model_subfolder_name, location, result)
        _logger.finest('WLSDPLY-06114', str(location), class_name=_class_name, method_name=_method_name)
        _logger.exiting(class_name=_class_name, method_name=_method_name, result=result)
        return result

    def _discover_single_folder(self, location):
        """
        Discover the attributes in the single folder at current location and allow the
        caller to continue the discover for any of its child folders. This is for required
        for certain folders that need to be handled differently.
        :param location: containing the current location information
        :return: folder result dictionary:
        """
        _method_name = '_discover_single_folder'
        _logger.entering(str(location), class_name=_class_name, method_name=_method_name)
        result = OrderedDict()
        subfolder_path = self._alias_helper.get_wlst_attributes_path(location)
        self._wlst_helper.cd(subfolder_path)
        self._populate_model_parameters(result, location)
        _logger.exiting(class_name=_class_name, method_name=_method_name)
        return result

    def _get_model_name(self, location, wlst_name):
        """
        Get the model folder name for the provided wlst mbean name. Throw an exception if the model name is
        not found in the aliases.
        :param location: context containing the current location information
        :param wlst_name: for which to locate the mbean name
        :return: model name for the folder
        :raises:DiscoverException:The mbean name is not in the alias folders
        """
        _method_name = '_get_model_name'
        _logger.finer('WLSDPLY-06117', wlst_name, self.get_context(location), class_name=_class_name,
                      method_name=_method_name)
        model_name = None
        # The below call will throw an exception if the folder does not exist; need to have that
        # exception thrown. The get_model_subfolder_name does not throw an exception if the alias
        # does not exist. We do not want an exception if the folder is just not available for the version
        mbean_type = self._alias_helper.get_wlst_mbean_type(location)
        if mbean_type:
            model_name = self._alias_helper.get_model_subfolder_name(location, wlst_name)
            _logger.finest('WLSDPLY-06118', model_name, wlst_name, class_name=_class_name, method_name=_method_name)
            if model_name is None:
                _logger.fine('WLSDPLY-06119', wlst_name, self._get_wlst_mode_string(), self._wls_version,
                             class_name=_class_name, method_name=_method_name)
        return model_name

    def _subfolder_exists(self, model_folder_name, location):
        """
        Check to see if the folder represented by the model folder name exists at the current loction
        :param model_folder_name: to check for at location
        :param location: context containing the current location information
        :return: True if the folder exists at the current location in the domain
        """
        temp_location = LocationContext(location)
        subfolders = self._find_subfolders(temp_location)
        temp_location.append_location(model_folder_name)
        wlst_mbean_type = self._alias_helper.get_wlst_mbean_type(temp_location)
        if subfolders:
            return wlst_mbean_type in subfolders
        return False

    def _add_att_handler(self, attribute_key, method):
        self._att_handler_map[attribute_key] = method

    def _convert_path(self, file_name):
        file_name_resolved = self._model_context.replace_token_string(file_name)
        if path_utils.is_relative_path(file_name_resolved):
            return convert_to_absolute_path(self._model_context.get_domain_home(), file_name_resolved)
        return file_name_resolved

    def _is_oracle_home_file(self, file_name):
        """
        Determine if the absolute file name starts with an oracle home.

        :param file_name: to check for oracle home or weblogic home
        :return: true if in oracle home location
        """
        py_str = str(file_name)
        return py_str.startswith(self._model_context.get_oracle_home()) or py_str.startswith(
            self._model_context.get_wl_home())

    def _get_wlst_mode_string(self):
        """
         Helper method to return the string representation for the online/offline mode of discovery.
         :return: String representation of mode
        """
        return WlstModes.from_value(self._wlst_mode)


def add_to_model_if_not_empty(dictionary, entry_name, entry_value):
    """
    Helper method for discover to add a non-empty value to the dictionary with the provided entry-name
    :param dictionary: to add the value
    :param entry_name: key to the value
    :param entry_value: to add to dictionary
    :return: True if the value was not empty and added to the dictionary
    """
    if entry_value:
        dictionary[entry_name] = entry_value
        return True
    return False


def convert_to_absolute_path(relative_to, file_name):
    """
    Transform the path by joining the relative_to before the file_name and converting the resulting path name to
    an absolute path name.
    :param relative_to: prefix of the path
    :param file_name: name of the file
    :return: absolute path of the relative_to and file_name
    """
    if not StringUtils.isEmpty(relative_to) and not StringUtils.isEmpty(file_name):
        file_name = os.path.join(relative_to, file_name)
    return file_name


def get_discover_logger_name():
    """
    Return the common logger used for all discover logging.
    :return: logger name
    """
    return _DISCOVER_LOGGER_NAME