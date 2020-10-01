"""Oedatamodel transformations from OEP (raw format) into other supported
formats."""
import csv
import zipfile
from enum import Enum
from io import BytesIO, StringIO
from typing import Optional

import jmespath


class OedataFormat(str, Enum):
    """Supplied oedatamodel response formats."""
    raw = 'raw'
    json_normalized = 'json_normalized'
    json_concrete = 'json_concrete'
    csv_normalized = 'csv_normalized'
    csv_concrete = 'csv_concrete'


def format_data(raw_json, data_format: OedataFormat):
    """Raw json is formatted according to given data format.

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
    if data_format == OedataFormat.json_concrete:
        return get_concrete_json(raw_json)
    if data_format == OedataFormat.csv_normalized:
        return get_normalized_csv(raw_json)
    if data_format == OedataFormat.csv_concrete:
        return get_concrete_csv(raw_json)
    return None


def get_data_indexes(raw_json):
    """Finds indexes of "id" columns in raw json oedatamodel.

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
    """Returns scenario data of given oedatamodel (raw)

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
    """Returns all data rows with given column names for given range in raw
    data.

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
        # Skip rows, if "id" column is not set (empty scalars or timeseries)
        if row[start] is None:
            continue
        table_data.append(dict(zip(column_names, row[start:end])))
    return table_data


def get_normalized_json(raw_json):
    """Formats raw oedatamodel into normalized json oedatamodel.

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
        raw_json, start=table_indexes[1], end=table_indexes[2],
    )
    timeseries = get_multiple_rows_from_data(
        raw_json, start=table_indexes[2], end=table_indexes[3],
    )
    scalars = get_multiple_rows_from_data(raw_json, start=table_indexes[3])
    return {
        'oed_scenario': scenario,
        'oed_data': data,
        'oed_scalars': scalars,
        'oed_timeseries': timeseries,
    }


def get_concrete_json(raw_json):
    """Formats raw oedatamodel into concrete json oedatamodel.

    Parameters
    ----------
    raw_json : dict
        Raw oedatamodel as json/dict from OEP

    Returns
    -------
    dict
        Concrete oedatamodel
    """
    normalized_json = get_normalized_json(raw_json)
    concrete_json = {
        'oed_scenario': normalized_json['oed_scenario'],
        'oed_scalars': [],
        'oed_timeseries': [],
    }
    for data in normalized_json['oed_data']:
        data_id = data['id']
        entry_index = 'oed_scalars'
        entry = jmespath.search(f'[?id==`{data_id}`] | [0]', normalized_json['oed_scalars'])
        if entry is None:
            entry_index = 'oed_timeseries'
            entry = jmespath.search(f'[?id==`{data_id}`] | [0]', normalized_json['oed_timeseries'])
        concrete_entry = {**data, **{k: v for k, v in entry.items() if k != 'id'}}
        concrete_json[entry_index].append(concrete_entry)
    return concrete_json


def get_normalized_csv(raw_json):
    normalized_json = get_normalized_json(raw_json)
    return create_zip_csv(normalized_json)


def get_concrete_csv(raw_json):
    concrete_json = get_concrete_json(raw_json)
    return create_zip_csv(concrete_json)


def create_zip_csv(json):
    zipped_file = BytesIO()
    with zipfile.ZipFile(zipped_file, 'a', zipfile.ZIP_DEFLATED) as zipped:
        for name, data in json.items():
            csv_data = StringIO()
            writer = csv.writer(csv_data, delimiter=',')
            if isinstance(data, dict):
                writer.writerow(data.keys())
                writer.writerow(data.values())
            elif isinstance(data, list):
                writer.writerow(data[0].keys())
                for row in data:
                    writer.writerow(row.values())
            else:
                raise TypeError("Unknown type to create csv from")
            csv_data.seek(0)
            csv_buffer = csv_data.read()
            zipped.writestr(f"{name}.csv", csv_buffer)
    zipped_file.seek(0)
    return zipped_file
