"""
Copyright (c) 2017, 2018, Oracle and/or its affiliates. All rights reserved.
The Universal Permissive License (UPL), Version 1.0
"""
import copy
from org.python.modules import jarray
import re
from sets import Set

from java.io import File
from java.lang import Class
import java.lang.Exception as JException
from java.lang import Long
from java.lang import RuntimeException
from java.lang import String
from java.util import Properties

from oracle.weblogic.deploy.util import TypeUtils
from oracle.weblogic.deploy.util import VersionException
from oracle.weblogic.deploy.util import VersionUtils

from wlsdeploy.aliases.alias_constants import ChildFoldersTypes
from wlsdeploy.aliases.alias_jvmargs import JVMArguments
from wlsdeploy.exception import exception_helper
from wlsdeploy.logging.platform_logger import PlatformLogger

from wlsdeploy.aliases.alias_constants import ATTRIBUTES
from wlsdeploy.aliases.alias_constants import COMMA_DELIMITED_STRING
from wlsdeploy.aliases.alias_constants import DELIMITED_STRING
from wlsdeploy.aliases.alias_constants import JARRAY
from wlsdeploy.aliases.alias_constants import LIST
from wlsdeploy.aliases.alias_constants import PATH_SEPARATOR_DELIMITED_STRING
from wlsdeploy.aliases.alias_constants import PREFERRED_MODEL_TYPE
from wlsdeploy.aliases.alias_constants import SECURITY_PROVIDER_FOLDER_PATHS
from wlsdeploy.aliases.alias_constants import SEMI_COLON_DELIMITED_STRING
from wlsdeploy.aliases.alias_constants import SPACE_DELIMITED_STRING
from wlsdeploy.aliases.alias_constants import WLST_ATTRIBUTES_PATH
from wlsdeploy.aliases.alias_constants import WLST_CREATE_PATH
from wlsdeploy.aliases.alias_constants import WLST_LIST_PATH
from wlsdeploy.aliases.alias_constants import WLST_PATH
from wlsdeploy.aliases.alias_constants import WLST_PATHS
from wlsdeploy.aliases.alias_constants import WLST_READ_TYPE
from wlsdeploy.aliases.alias_constants import WLST_TYPE
from wlsdeploy.aliases.alias_constants import WLST_SUBFOLDERS_PATH

_class_name = 'alias_utils'
_logger = PlatformLogger('wlsdeploy.aliases')
_server_start_location_folder_path = '/Server/ServerStart'
_server_start_argument_attribute_name = 'Argument'
_windows_path_regex = re.compile(r'^[a-zA-Z]:[\\/].*')


def merge_model_and_existing_lists(model_list, existing_list, string_list_separator_char=','):
    """
    Merge the two lists so that the resulting list contains all of the elements in both lists one time.
    :param model_list: the list to merge
    :param existing_list: the existing list
    :param string_list_separator_char: the character separator to use to split the lists if either list is a string
    :return: the merged list as a list or a string, depending on the type of the model_list
    :raises: DeployException: if either list is not either a string or a list
    """
    _method_name = 'merge_model_and_existing_lists'

    _logger.entering(model_list, existing_list, string_list_separator_char,
                     class_name=_class_name, method_name=_method_name)
    if existing_list is None or len(existing_list) == 0:
        result = model_list
    elif model_list is None or len(model_list) == 0:
        result = existing_list
        if type(model_list) is str and type(existing_list) is not str:
            result = string_list_separator_char.join(existing_list)
    else:
        model_list_is_string = False
        if type(model_list) is str:
            model_list_is_string = True
            model_set = Set([x.strip() for x in model_list.split(string_list_separator_char)])
        elif type(model_list) is list:
            model_set = Set(model_list)
        else:
            ex = exception_helper.create_deploy_exception('WLSDPLY-09114', str(type(model_list)))
            _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
            raise ex

        if type(existing_list) is str:
            existing_set = Set([x.strip() for x in existing_list.split(string_list_separator_char)])
        elif type(existing_list) is list:
            existing_set = Set(existing_list)
        else:
            ex = exception_helper.create_deploy_exception('WLSDPLY-09115', str(type(existing_list)))
            _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
            raise ex

        result = list(existing_set.union(model_set))
        if model_list_is_string:
            result = string_list_separator_char.join(result)

    _logger.exiting(class_name=_class_name, method_name=_method_name, result=result)
    return result

def merge_model_and_existing_properties(model_props, existing_props, string_props_separator_char=','):
    """
    Merge the two properties objects so that the resulting properties contains all of the elements in both properties.
    :param model_props: the model properties
    :param existing_props: the existing properties
    :param string_props_separator_char: the property delimiter
    :return: the merged properties object as a java.util.Properties or a string,
             depending on the type of the model_props
    :raises: DeployException: if either properties is not either a string or a java.util.Properties object
    """
    _method_name = 'merge_model_and_existing_lists'

    _logger.entering(model_props, existing_props, string_props_separator_char,
                     class_name=_class_name, method_name=_method_name)
    if existing_props is None or len(existing_props) == 0:
        result = model_props
    elif model_props is None or len(model_props) == 0:
        result = existing_props
        if type(model_props) is str and type(existing_props) is not str:
            result = _properties_to_string(existing_props, string_props_separator_char)
    else:
        model_props_is_string = False
        if type(model_props) is str:
            model_props_is_string = True
            model_properties = _string_to_properties(model_props, string_props_separator_char)
        elif TypeUtils.isInstanceOfClass(Properties().getClass(), model_props):
            model_properties = model_props
        else:
            ex = exception_helper.create_deploy_exception('WLSDPLY-09118', str(type(model_props)))
            _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
            raise ex

        if type(existing_props) is str:
            existing_properties = _string_to_properties(existing_props, string_props_separator_char)
        elif TypeUtils.isInstanceOfClass(Properties().getClass(), existing_props):
            existing_properties = existing_props
        else:
            ex = exception_helper.create_deploy_exception('WLSDPLY-09119', str(type(existing_props)))
            _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
            raise ex

        for entry_set in model_properties.entrySet():
            key = entry_set.getKey()
            value = entry_set.getValue()
            existing_properties.setProperty(key, value)
        if model_props_is_string:
            result = _properties_to_string(existing_properties, string_props_separator_char)
        else:
            result = existing_properties

    _logger.exiting(class_name=_class_name, method_name=_method_name, result=result)
    return result

def merge_server_start_argument_values(model_args, existing_args):
    """
    Merge the two arguments strings.
    :param model_args: the new string from the model
    :param existing_args: the old string (e.g., from WLST)
    :return: the resulting merged string
    """
    _method_name = 'merge_server_start_argument_values'

    _logger.entering(model_args, existing_args, class_name=_class_name, method_name=_method_name)
    if model_args is None or len(model_args) == 0:
        result = existing_args
    elif existing_args is None or len(existing_args) == 0:
        result = model_args
    else:
        new_args = JVMArguments(_logger, model_args)
        old_args = JVMArguments(_logger, existing_args)
        merged_args = old_args.merge_jvm_arguments(new_args)
        result = merged_args.get_arguments_string()
    _logger.exiting(class_name=_class_name, method_name=_method_name, result=result)
    return result

def count_substring_occurrences(substring, string):
    """
    Count the number of occurrences of a substring in a string
    :param substring: the substring
    :param string: the string
    :return: the number of occurrences
    """
    count = 0
    start = 0
    while start < len(string):
        start = string.find(substring, start)
        if start == -1:
            break
        else:
            count += 1
            start += len(substring)
    return count

def compute_base_path(model_category_name, raw_model_category_dictionary):
    """
    Compute the base path to use from the model category dictionary.
    :param model_category_name: the model category name for the dictionary (used for error handling only)
    :param raw_model_category_dictionary: the raw dictionary
    :return: the new base path (e.g., '/Partition${:s}/%PARTITION%')
    :raises: AliasException: if bad alias data is encountered
    """
    _method_name = 'compute_base_path'

    if WLST_SUBFOLDERS_PATH in raw_model_category_dictionary:
        base_path_index = raw_model_category_dictionary[WLST_SUBFOLDERS_PATH]
    elif WLST_ATTRIBUTES_PATH in raw_model_category_dictionary:
        base_path_index = raw_model_category_dictionary[WLST_ATTRIBUTES_PATH]
    else:
        ex = exception_helper.create_alias_exception('WLSDPLY-08063', WLST_ATTRIBUTES_PATH, model_category_name)
        _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
        raise ex

    if WLST_PATHS in raw_model_category_dictionary:
        if base_path_index in raw_model_category_dictionary[WLST_PATHS]:
            base_path = raw_model_category_dictionary[WLST_PATHS][base_path_index]
        else:
            ex = exception_helper.create_alias_exception('WLSDPLY-08064', base_path_index,
                                                         WLST_PATHS, model_category_name)
            _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
            raise ex
    else:
        ex = exception_helper.create_alias_exception('WLSDPLY-08065', WLST_PATHS, model_category_name)
        _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
        raise ex

    _logger.exiting(class_name=_class_name, method_name=_method_name, result=base_path)
    return base_path

def update_version_range_dict(version_range_dict, mode, version_range):
    """
    Update the unmatched attribute version range dictionary based on the specified mode and version range.
    :param version_range_dict: the current version range dictionary
    :param mode: the WLST mode applicable to the new version range
    :param version_range: the new version range to add
    :raises: VersionException: if an error occurs
    """
    if mode == 'both':
        _update_version_range_dict_mode(version_range_dict, 'offline', version_range)
        _update_version_range_dict_mode(version_range_dict, 'online', version_range)
    elif mode == 'offline':
        _update_version_range_dict_mode(version_range_dict, 'offline', version_range)
    elif mode == 'online':
        _update_version_range_dict_mode(version_range_dict, 'online', version_range)
    return

def parse_curly_braces(value):
    """
    Parse out the curly braces.
    :param value: the value with any curly braces
    :return: the modified value
    """
    alist = [value, value]

    if alist[0] is not None:
        for i in range(len(alist)):
            while '${' in alist[i] and ':' in alist[i] and '}' in alist[i]:
                idx1 = alist[i].index('${')
                idx2 = alist[i].index(':')
                idx3 = alist[i].index('}')
                if i == 0:
                    alist[i] = alist[i][0:idx1]+alist[i][idx1+2:idx2]+alist[i][idx3+1:]
                else:
                    alist[i] = alist[i][0:idx1]+alist[i][idx2+1:idx3]+alist[i][idx3+1:]
    return alist

def get_missing_name_tokens(wlst_path):
    """
    Get the unique list of unresolved name tokens, each token will only appear in the list once regardless
    of how many times it appears in the path.
    :param wlst_path: the path that may contain unresolved tokens
    :return: the list of unresolved tokens, or an empty list if not unresolved tokens were found
    """
    missing_name_tokens = dict()
    if '%' in wlst_path:
        p = re.compile("%[A-Z_]*%")
        tokens = p.findall(wlst_path)
        if tokens is not None:
            for token in tokens:
                missing_name_tokens[token[1:-1]] = True
    return missing_name_tokens.keys()

def resolve_path_tokens(location, path_name, folder_dict):
    """
    Resolve any path tokens in all paths within the folder
    :param location: the location of the folder
    :param path_name: the path name
    :param folder_dict: the dictionary for the folder
    :return: a new dictionary with all path tokens resolved
    :raises: AliasException: if an error occurs while processing the path tokens
    """
    _method_name = 'resolve_path_tokens'

    #
    # With folder versioning in place, a folder dictionary will be None if it is not relevant to the
    # current WLS version.  As such, just return None since there are no paths to resolve.
    #
    if folder_dict is None:
        return None

    #
    # Now that we have the target dictionary, we need to make a copy of it and replace the path tokens.
    #
    resolved_dict = copy.deepcopy(folder_dict)
    if WLST_PATHS in resolved_dict:
        wlst_paths_dict = resolved_dict[WLST_PATHS]
        for path_key in wlst_paths_dict:
            path_value = wlst_paths_dict[path_key]
            wlst_paths_dict[path_key] = replace_tokens_in_path(location, path_value)
    else:
        ex = exception_helper.create_alias_exception('WLSDPLY-08029', path_name)
        _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
        raise ex

    #
    # Resolve the wlst path attributes in the model
    #
    if WLST_ATTRIBUTES_PATH in resolved_dict:
        wlst_path_key = resolved_dict[WLST_ATTRIBUTES_PATH]
        if wlst_path_key in wlst_paths_dict:
            resolved_dict[WLST_ATTRIBUTES_PATH] = wlst_paths_dict[wlst_path_key]
        else:
            ex = exception_helper.create_alias_exception('WLSDPLY-08035', path_name, WLST_ATTRIBUTES_PATH,
                                                         wlst_path_key, WLST_PATHS)
            _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
            raise ex
    else:
        ex = exception_helper.create_alias_exception('WLSDPLY-08036', path_name, WLST_ATTRIBUTES_PATH)
        _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
        raise ex

    if WLST_SUBFOLDERS_PATH in resolved_dict:
        wlst_path_key = resolved_dict[WLST_SUBFOLDERS_PATH]
        if wlst_path_key in wlst_paths_dict:
            resolved_dict[WLST_SUBFOLDERS_PATH] = wlst_paths_dict[wlst_path_key]
        else:
            ex = exception_helper.create_alias_exception('WLSDPLY-08035', path_name, WLST_SUBFOLDERS_PATH,
                                                         wlst_path_key, WLST_PATHS)
            _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
            raise ex
    else:
        # default back to the attributes path
        resolved_dict[WLST_SUBFOLDERS_PATH] = resolved_dict[WLST_ATTRIBUTES_PATH]

    if WLST_LIST_PATH in resolved_dict:
        wlst_path_key = resolved_dict[WLST_LIST_PATH]
        if wlst_path_key in wlst_paths_dict:
            resolved_dict[WLST_LIST_PATH] = wlst_paths_dict[wlst_path_key]
        else:
            ex = exception_helper.create_alias_exception('WLSDPLY-08035', path_name, WLST_LIST_PATH,
                                                         wlst_path_key, WLST_PATHS)
            _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
            raise ex
    else:
        # default back to the parent folder of the attributes path
        attr_path = resolved_dict[WLST_ATTRIBUTES_PATH]
        resolved_dict[WLST_LIST_PATH] = strip_trailing_folders_in_path(attr_path)

    if WLST_CREATE_PATH in resolved_dict:
        wlst_path_key = resolved_dict[WLST_CREATE_PATH]
        if wlst_path_key in wlst_paths_dict:
            resolved_dict[WLST_CREATE_PATH] = wlst_paths_dict[wlst_path_key]
        else:
            ex = exception_helper.create_alias_exception('WLSDPLY-08035', path_name, WLST_CREATE_PATH,
                                                         wlst_path_key, WLST_PATHS)
            _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
            raise ex
    else:
        # default back to the grandparent folder of the attributes path
        attr_path = resolved_dict[WLST_ATTRIBUTES_PATH]
        resolved_dict[WLST_CREATE_PATH] = strip_trailing_folders_in_path(attr_path, 2)

    #
    # Now that the wlst_paths have been resolved, resolve the references to them in each of the attributes
    #
    if ATTRIBUTES in resolved_dict:
        attrs_dict = resolved_dict[ATTRIBUTES]
        for attr_name in attrs_dict:
            attr_dict = attrs_dict[attr_name]

            if WLST_PATH in attr_dict:
                wlst_path_key = attr_dict[WLST_PATH]

                if wlst_path_key in wlst_paths_dict:
                    attr_dict[WLST_PATH] = wlst_paths_dict[wlst_path_key]
                else:
                    ex = exception_helper.create_alias_exception('WLSDPLY-08025', attr_name,
                                                                 path_name, wlst_path_key)
                    _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
                    raise ex
            else:
                ex = exception_helper.create_alias_exception('WLSDPLY-08026', attr_name, path_name)
                _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
                raise ex
    return resolved_dict

def resolve_path_index(folder_dict, paths_index, path_attribute_name_used, location):
    """
    Get the path for the specified path index.
    :param folder_dict: the folder dictionary
    :param paths_index: the path index key
    :param path_attribute_name_used: the path attribute name used
    :param location: the location of the folder
    :return: the path for the specified path index
    :raises: AliasException: if an error occurs while location the path of the specified path index
    """
    _method_name = 'resolve_path_index'

    # Don't log folder dictionary because it is likely very large
    _logger.entering(paths_index, path_attribute_name_used, str(location),
                     class_name=_class_name, method_name=_method_name)
    if WLST_PATHS in folder_dict:
        if paths_index in folder_dict[WLST_PATHS]:
            tokenized_path = folder_dict[WLST_PATHS][paths_index]
        else:
            ex = exception_helper.create_alias_exception('WLSDPLY-08033', location.get_folder_path(),
                                                         path_attribute_name_used, paths_index, WLST_PATHS)
            _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
            raise ex
    else:
        ex = exception_helper.create_alias_exception('WLSDPLY-08034', location.get_folder_path(), WLST_PATHS)
        _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
        raise ex
    _logger.exiting(class_name=_class_name, method_name=_method_name, result=tokenized_path)
    return tokenized_path

def replace_tokens_in_path(location, path):
    """
    Replace the tokens in the path using the supplied location's name tokens.
    :param location: the location to use
    :param path: the path
    :return: the path with all tokens replaced
    :raises: AliasException: if an error occurs while processing the path tokens
    """
    _method_name = 'replace_tokens_in_path'

    _logger.entering(str(location), path, class_name=_class_name, method_name=_method_name)
    name_tokens = location.get_name_tokens()
    new_path = path
    if name_tokens:
        for key, value in name_tokens.iteritems():
            new_path = new_path.replace('%s%s%s' % ('%', key, '%'), value)

    missing_name_token = get_missing_name_tokens(new_path)

    if len(missing_name_token) > 0:
        ex = exception_helper.create_alias_exception('WLSDPLY-08000', new_path, missing_name_token)
        _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
        raise ex
    _logger.exiting(class_name=_class_name, method_name=_method_name, result=new_path)
    return new_path

def get_token_value(location, value):
    """
    Replace the name token, if present, in the specified value with the token value from the location
    :param location: the location to use
    :param value: the value
    :return: the value or the location name token value if the value was a name token
    :raises: AliasException:
    """
    _method_name = 'get_token_value'
    result = value
    if value is not None and value.startswith('%') and value.endswith('%'):
        token_name = value[1:-1]
        name_tokens = location.get_name_tokens()
        if token_name in name_tokens:
            result = name_tokens[token_name]
        else:
            ex = exception_helper.create_alias_exception('WLSDPLY-08087', token_name)
            _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
            raise ex
    return result

def strip_trailing_folders_in_path(path, number_of_folders=1):
    """
    Remove one or more directories from the end of the specified path.  Note that if the number of
    directories to remove is less than or equal to the number of slashes, not counting any trailing
    slash that may be present.
    :param path: the path from which to remove the directory(ies)
    :param number_of_folders: the number of directories to remove, by default, only one is removed
    :return: the resulting path
    """
    _method_name = 'strip_trailing_folders_in_path'

    _logger.entering(path, number_of_folders, class_name=_class_name, method_name=_method_name)
    path_len = len(path)

    # remove any trailing slash unless the entire path is '/'
    my_path = path
    if path.endswith('/') and path_len > 1:
        my_path = path[:-1]
        path_len -= 1

    slashes_in_path = my_path.count('/')
    if slashes_in_path > number_of_folders:
        for i in range(number_of_folders):
            slash_index = my_path.rfind('/')
            my_path = my_path[:slash_index]
        result = my_path
    else:
        result = '/'
    _logger.exiting(class_name=_class_name, method_name=_method_name, result=result)
    return result

def compute_folder_name_from_path(path_name):
    """
    Get the current folder name from the path
    :param path_name: the path
    :return: the current folder name, or DOMAIN if the path is None, empty or '/'
    """
    _method_name = 'compute_folder_name_from_path'

    _logger.entering(path_name, class_name=_class_name, method_name=_method_name)
    if path_name is None or len(path_name) < 2:
        result = 'DOMAIN'
    else:
        index = path_name.rfind('/')
        if index < 0:
            result = path_name
        else:
            result = path_name[index + 1:]
    _logger.exiting(class_name=_class_name, method_name=_method_name, result=result)
    return result

def convert_boolean(value):
    """
    Convert the specified value into a boolean
    :param value: the value to convert
    :return: True or False, depending on the specified value
    """
    result = False
    if value is not None:
        if type(value) is bool:
            result = value
        elif type(value) is int:
            if value == 1:
                result = True
            elif value == 0:
                result = False
        elif type(value) is str:
            if value.lower() == 'true':
                result = True
            elif value.lower() == 'false':
                result = False
    return result

def is_attribute_server_start_arguments(location, model_attribute_name):
    """
    Is the location and attribute the Server/ServerStart folder's Argument attribute
    :param location: location
    :param model_attribute_name: attribute name
    :return: True if so, False otherwise
    """
    return location.get_folder_path() == _server_start_location_folder_path and \
           model_attribute_name == _server_start_argument_attribute_name

def compute_delimiter_from_data_type(data_type, value):
    """
    Compute the delimiter from the data type
    :param data_type: the data_type
    :param value: the value of the field
    :return: the delimiter
    """
    delimiter = None
    if data_type in (COMMA_DELIMITED_STRING, DELIMITED_STRING):
        delimiter = ','
    elif data_type == SEMI_COLON_DELIMITED_STRING:
        delimiter = ';'
    elif data_type == SPACE_DELIMITED_STRING:
        delimiter = ' '
    elif data_type == PATH_SEPARATOR_DELIMITED_STRING:
        delimiter = _get_path_separator(value)
    return delimiter

def compute_read_data_type_and_delimiter_from_attribute_info(attribute_info, value):
    """
    Get the WLST read data type and delimiter from the attribute
    :param attribute_info: attribute dictionary
    :param value: the attribute value
    :return: the data type and delimiter
    """
    data_type = None
    delimiter = None

    if WLST_TYPE in attribute_info:
        data_type = attribute_info[WLST_TYPE]
        delimiter = compute_delimiter_from_data_type(data_type, value)

    if WLST_READ_TYPE in attribute_info:
        data_type = attribute_info[WLST_READ_TYPE]
        read_delimiter = compute_delimiter_from_data_type(data_type, value)
        if read_delimiter is not None:
            delimiter = read_delimiter

    if PREFERRED_MODEL_TYPE in attribute_info:
        data_type = attribute_info[PREFERRED_MODEL_TYPE]
        #
        # This code does not consider the delimiter defined by the preferred_model_type field unless there is
        # no other delimiter defined by wlst_type or wlst_read_type.  This is required to handle the use case
        # where the value read from WLST had a different separator than the preferred_model_type.
        #
        if delimiter is None:
            delimiter = compute_delimiter_from_data_type(data_type, value)

    return data_type, delimiter

def get_number_of_directories_to_strip(desired_path_type, actual_path_type):
    """
    Compute the number of directories to strip off the path based on the desired path and actual path types.
    :param desired_path_type: the desired path type
    :param actual_path_type: the actual path type
    :return: the number of directories to strip off the actual path to derive the desired path type
    """
    if actual_path_type == desired_path_type:
        result = 0
    else:
        desired_value = _get_value_for_path_type(desired_path_type)
        actual_value = _get_value_for_path_type(actual_path_type)
        result = desired_value - actual_value
    return result

def convert_to_type(data_type, value, subtype=None, delimiter=None):
    """
    Convert the value to the specified type.
    :param data_type: the type
    :param value: the value
    :return: the value converted to the specified type
    """
    #
    # TypeUtils.convertToType doesn't work for passwords...
    #
    if value is not None and data_type == 'password':
        # The password is an array of bytes coming back from the WLST get() method and only
        # java.lang.String() is able to properly convert it to the cipher text string.  However,
        # we don't really want to return a java.lang.String to the caller so convert that Java
        # String back to a Python string...ugly but effective.
        new_value = str(String(value))
    else:
        new_value = TypeUtils.convertToType(data_type, value, delimiter)

        if new_value is not None:
            if data_type == 'long':
                new_value = Long(new_value)
            elif data_type == JARRAY:
                if subtype is None or subtype == 'java.lang.String':
                    new_value = _create_string_array(new_value)
                else:
                    new_value = _create_mbean_array(new_value, subtype)
            elif data_type == LIST:
                new_value = list(new_value)
            elif data_type in (COMMA_DELIMITED_STRING, DELIMITED_STRING, SEMI_COLON_DELIMITED_STRING,
                               SPACE_DELIMITED_STRING, PATH_SEPARATOR_DELIMITED_STRING):
                #
                # This code intentionally ignores the delimiter value passed in and computes it from the data type.
                # This is required to handle the special case where the value we read from WLST might have a
                # different delimiter than the model value.  In this use case, the value passed into the method
                # is the WLST value delimiter and the data_type is the preferred_model_type, so we compute the
                # model delimiter from the data_type directly.
                #
                delimiter = compute_delimiter_from_data_type(data_type, new_value)
                new_value = delimiter.join(new_value)

    return new_value

def get_child_folder_type_value_from_enum_value(child_folder_type):
    """
    Get the child_folder_type value from the enum value
    :param child_folder_type: the enum value
    :return: the child_folder_type value
    """
    _method_name = 'get_child_folder_type_value_from_enum_value'

    try:
        enum_text = ChildFoldersTypes.from_value(child_folder_type)
        result = enum_text.lower()
    except ValueError, ve:
        ex = exception_helper.create_alias_exception('WLSDPLY-08100', child_folder_type, str(ve), error=ve)
        _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
        raise ex
    return result

def is_security_provider_location(location):
    """
    Does the current location refer to a security provider?
    :param location: the location
    :return: True, if the location refers to a security provider, False otherwise
    """
    return location.get_folder_path() in SECURITY_PROVIDER_FOLDER_PATHS

###############################################################################
#                              Private functions                              #
###############################################################################

def _get_path_separator(value):
    """
    Get the path separator to use for this value.  If the value is a string and contains
    :param value: the value
    :return: the computed path separator
    """
    _method_name = '_get_path_separator'
    _logger.entering(value, class_name=_class_name, method_name=_method_name)

    result = File.pathSeparator
    if type(value) is str and len(value) > 0:
        # If the value has a windows separator or a single directory that starts with a drive letter
        if ';' in value or _windows_path_regex.match(value):
            result = ';'
        elif ':' in value:
            result = ':'
    _logger.exiting(class_name=_class_name, method_name=_method_name, result=result)
    return result

def _update_version_range_dict_mode(version_range_dict, wlst_mode, version_range):
    """
    update the version range dictionary element specified by the WLST mode using the new version range.
    :param version_range_dict: the current version range dictionary
    :param wlst_mode: which of the two WLST modes elements to update in the dictionary
    :param version_range: the new version range
    :raises: VersionException: if an error occurs
    """
    if wlst_mode in version_range_dict:
        current_value = version_range_dict[wlst_mode]
        new_value = _merge_version_ranges(current_value, version_range)
        version_range_dict[wlst_mode] = new_value
    else:
        version_range_dict[wlst_mode] = version_range
    return

def _merge_version_ranges(current_range, range_to_add):
    """
    Merge two version ranges into a single range covering both input ranges.
    :param current_range: one version range
    :param range_to_add: another version range
    :return: the merged version range
    :raises: VersionException: if an error occurs
    """
    _method_name = '_merge_version_ranges'

    _logger.entering(current_range, range_to_add, class_name=_class_name, method_name=_method_name)
    current_inclusive = not current_range.startswith('(')
    range_to_add_inclusive = not range_to_add.startswith('(')

    current_low, current_high = _get_low_and_high_version_from_range(current_range)
    range_to_add_low, range_to_add_high = _get_low_and_high_version_from_range(range_to_add)

    low_compare = VersionUtils.compareVersions(current_low, range_to_add_low)
    if low_compare > 0:
        if range_to_add_inclusive:
            new_range = '[' + range_to_add_low + ','
        else:
            new_range = '(' + range_to_add_low + ','
    elif low_compare < 0:
        if current_inclusive:
            new_range = '[' + current_low + ','
        else:
            new_range = '(' + current_low + ','
    else:
        if range_to_add_inclusive or current_inclusive:
            new_range = '[' + current_low + ','
        else:
            new_range = '(' + current_low + ','

    current_inclusive = not current_range.endswith(')')
    range_to_add_inclusive = not range_to_add.endswith(')')

    if len(current_high) == 0 or len(range_to_add_high) == 0:
        new_range += ')'
    else:
        high_compare = VersionUtils.compareVersions(current_high, range_to_add_high)
        if high_compare > 0:
            if current_inclusive:
                new_range += current_high + ']'
            else:
                new_range += current_high + ')'
        elif high_compare < 0:
            if range_to_add_inclusive:
                new_range += range_to_add_high + ']'
            else:
                new_range += range_to_add_high + ')'
        else:
            if range_to_add_inclusive or current_inclusive:
                new_range += current_high + ']'
            else:
                new_range += current_high + ')'

    _logger.exiting(class_name=_class_name, method_name=_method_name, result=new_range)
    return new_range

def _get_low_and_high_version_from_range(version_range):
    """
    Parse a version range into its low and high components.
    :param version_range: the version range
    :return: the low and high version components, an empty string is returned if there is no upper bound
    """
    _method_name = '_get_low_and_high_version_from_range'

    _logger.entering(version_range, class_name=_class_name, method_name=_method_name)
    try:
        versions = VersionUtils.getLowerAndUpperVersionStrings(version_range)
    except VersionException, ve:
        ex = exception_helper.create_alias_exception('WLSDPLY-08059', version_range, ve.getLocalizedMessage(), error=ve)
        _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
        raise ex

    if len(versions) == 2:
        low = versions[0]
        high = versions[1]
        if high is None:
            high = ''
    else:
        low = versions[0]
        high = low
    _logger.exiting(class_name=_class_name, method_name=_method_name, result=[low, high])
    return low, high

def _properties_to_string(props, string_props_separator_char):
    """
    Convert a java.util.Properties object into a string
    :param props: the java.util.Properties object
    :param string_props_separator_char: the delimiter to use to separate properties
    :return: the delimited string representing the properties object
    """
    _method_name = '_properties_to_string'

    _logger.entering(props, string_props_separator_char, class_name=_class_name, method_name=_method_name)
    if props is None:
        result = ''
    elif type(props) is str:
        result = props
    else:
        result = ''
        for entry_set in props.entrySet():
            key = entry_set.getKey()
            value = entry_set.getValue()
            if len(result) > 0:
                result += string_props_separator_char
            result += str(key) + '=' + str(value)
    _logger.exiting(class_name=_class_name, method_name=_method_name, result=result)
    return result

def _string_to_properties(string, string_props_separator_char):
    """
    Convert a delimited string into a java.util.Properties object
    :param string: the delimited string
    :param string_props_separator_char:, the delimiter used to separate properties
    :return: the java.util.Properties object
    :raises: DeployException: if the string is not formatted as expected
             (i.e., name=value pairs separated by the specified separator)
    """
    _method_name = '_string_to_properties'

    _logger.entering(string, string_props_separator_char, class_name=_class_name, method_name=_method_name)
    result = Properties()
    if string is not None and len(string) > 0:
        elements = string.split(string_props_separator_char)
        for element in elements:
            stripped_element = element.strip()
            prop_key_value = stripped_element.split('=')
            if len(prop_key_value) == 2:
                key = prop_key_value[0].strip()
                value = prop_key_value[1].strip()
                result.setProperty(key, value)
            else:
                ex = exception_helper.create_deploy_exception('WLSDPLY-09117', string)
                _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
                raise ex
    _logger.exiting(class_name=_class_name, method_name=_method_name, result=result)
    return result

def _get_value_for_path_type(path_type):
    """
    Compute a numeric value for the path type based on the number of directories above the base wlst_attributes_path.

    :param path_type: path type
    :return: the numeric value
    """
    _method_name = '_get_value_for_path_type'

    _logger.entering(path_type, class_name=_class_name, method_name=_method_name)
    if path_type == WLST_CREATE_PATH:
        result = 2
    elif path_type == WLST_LIST_PATH:
        result = 1
    elif path_type == WLST_SUBFOLDERS_PATH or path_type == WLST_ATTRIBUTES_PATH:
        result = 0
    else:
        ex = exception_helper.create_alias_exception('WLSDPLY-08088', path_type)
        _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
        raise ex
    _logger.exiting(class_name=_class_name, method_name=_method_name, result=result)
    return result

def _create_string_array(iterable):
    """
    Create a jarray of java.lang.String suitable for WLST attributes that take list objects.
    This is mostly used for WLST online.
    :param iterable: a List object or other iterable type
    :return: a jarray containing the same contents as the provided iterable
    """
    array_len = len(iterable)
    myarray = jarray.zeros(array_len, String)
    idx = 0
    for element in iterable:
        myarray[idx] = element
        idx += 1
    return myarray

def _create_mbean_array(iterable, subtype):
    """
    Create a jarray of the subtype suitable for WLST attributes that take list objects.
    This is mostly used for WLST online.
    :param iterable: a List object or other iterable type
    :return: a jarray containing the same contents as the provided iterable
    """
    _method_name = '__create_mbean_array'
    array_len = len(iterable)

    try:
        clazz = Class.forName(subtype)
    except (JException, RuntimeException), e:
        ex = exception_helper.create_alias_exception('WLSDPLY-08077', subtype, e.getLocalizedMessage(), error=e)
        _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
        raise ex

    myarray = jarray.zeros(array_len, clazz)
    idx = 0
    for element in iterable:
        myarray[idx] = element
        idx += 1
    return myarray