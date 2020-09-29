
from enum import Enum
from typing import Optional

import jmespath


class OedataFormat(str, Enum):
    raw = 'raw'
    json_normalized = 'json_normalized'
    json_concrete = 'json_concrete'
    csv_normalized = 'csv_normalized'
    csv_concrete = 'csv_concrete'


def format_data(raw_json, data_format: OedataFormat):
    """
    Raw json is formatted according to given data format

    Parameters
    ----------
    raw_json : dict
        Raw oedatamodel as json/dict from OEP
    data_format : OedataFormat
        One of possible data formats (json/csv, normalized/concrete)

    Returns
    -------
    dict
        Output json/dict formatted by given data format
    """
    if data_format == OedataFormat.raw:
        return raw_json
    if data_format == OedataFormat.json_normalized:
        return get_normalized_json(raw_json)


def get_data_indexes(raw_json):
    """
    Finds indexes of "id" columns in raw json oedatamodel

    Parameters
    ----------
    raw_json : dict
        Raw oedatamodel as json/dict from OEP

    Returns
    -------
    List[int]
        Indexes of "id" columns in raw json
    """
    return [i for i, column in enumerate(raw_json['description']) if column[0] == 'id']


def get_scenario_data(raw_json, scenario_columns: int):
    """
    Returns scenario data of given oedatamodel (raw)

    Parameters
    ----------
    raw_json : dict
        Raw oedatamodel as json/dict from OEP
    scenario_columns : int
        Amount of scenario columns

    Returns
    -------
    dict
        Scenario data from oedatamodel
    """
    scenario_data = {}
    for i in range(scenario_columns):
        column_name = raw_json['description'][i][0]
        # As scenario data is same in every row, we only need first row:
        scenario_data[column_name] = raw_json['data'][0][i]
    return scenario_data


def get_multiple_rows_from_data(raw_json, start: int, end: Optional[int] = None):
    """
    Returns all data rows with given column names for given range in raw data

    Parameters
    ----------
    raw_json : dict
        Raw oedatamodel as json/dict from OEP
    start : int
        Starting index for columns to use in given rows
    end : Optional[int]
        Ending index for columns, if nothing is given, full length is taken

    Returns
    -------
    List[dict]
        List of all rows, containing dict of column names and data
    """
    column_names = [column[0] for column in raw_json['description'][start:end]]
    table_data = []
    for row in raw_json['data']:
        # Skip rows, if "id" column is not set (empty scalars or timeseries):
        if row[start] is None:
            continue
        table_data.append(dict(zip(column_names, row[start:end])))
    return table_data


def get_normalized_json(raw_json):
    """
    Formats raw oedatamodel into normalized oedatamodel

    Parameters
    ----------
    raw_json : dict
        Raw oedatamodel as json/dict from OEP

    Returns
    -------
    dict
        Normalized oedatamodel
    """
    table_indexes = get_data_indexes(raw_json)
    scenario = get_scenario_data(raw_json, table_indexes[1])
    data = get_multiple_rows_from_data(
        raw_json, start=table_indexes[1], end=table_indexes[2])
    timeseries = get_multiple_rows_from_data(
        raw_json, start=table_indexes[2], end=table_indexes[3])
    scalars = get_multiple_rows_from_data(raw_json, start=table_indexes[3])
    return {'oed_scenario': scenario, 'oed_data': data, 'oed_scalars': scalars, 'oed_timeseries': timeseries}
