from abc import ABC
import asyncio
import glob
import math
import os
from datetime import datetime, timedelta
from multiprocessing.context import SpawnContext
from multiprocessing.pool import Pool
from pathlib import Path
from typing import Literal, Optional

import aiohttp
import numpy as np
import pandas as pd
import sklearn.tree

try:
    from . import api_async, enums, transport
except (ImportError, ModuleNotFoundError):
    import api_async
    import enums
    import transport


def _write_raw_csv_worker(path: Path, columns: dict[str, type], etas: list) -> None:
    df = pd.DataFrame([eta for eta in etas if eta['eta'] is not None],
                      columns=columns.keys())

    if len(df) == 0:
        return
    try:
        old_df = pd.read_csv(path,
                             index_col=0,
                             low_memory=True,
                             dtype=columns)
    except (pd.errors.ParserError, FileNotFoundError):
        old_df = pd.DataFrame(columns=columns.keys())

    pd.concat([old_df, df[df['eta_seq'] == 1]]) \
        .reset_index(drop=True) \
        .to_csv(path, mode='w', index=True)


def _calculate_etas_error(df: pd.DataFrame) -> pd.DataFrame:
    for _, group in df.groupby('stop'):
        schedules = []
        last_tta, last_timestamp = float('inf'), None
        etas = tuple(group.itertuples())

        # Normal
        #   Example: 166, 142, 109, *-72, 390
        # Close TTA between two consecutive schedule
        #   Example: 234, 220, 126, 69, 4, *-65, 109 , 33, -46, 4, -60, -4, *-70, 245, 149, 149, 43, *-26, 137
        #   Example: *-4, 99, 59, 28, *-11, 61, 10, 55, *7, 280
        # Arrival at positive TTA
        #   Example: 303, 252, 201, 142, 141, 11, *-54, 180, 120, 36, 11, *11, 315
        #   Example: 244, 215, 214, 144, 80, *2, 132, 84
        #   Example: 202, 143, 83, *23, 186, 171, 143
        # [!] TTA jump up at the middle
        #   Example: 520, 460, 400, 338, [279, 298,] 255, 202, 139, 64, 11, 6, -81, 634
        #   Example: 193, 135, 71, 67, 52, 41, 0, *-71, [75, 78, 78, 79, 51,] 9, *-36, 91, 61
        # Extreme fluctuation
        #   Example: 112, 94, -7, -42, 0, *-74, 145, 86
        #   Example: 155, 94, 88, 4, -34, 0, -60, *-18, 135, 83
        #   Example: 154, 106, 106, 63, 0, -44, 2, *-20, 87, 73, *-7, 88
        #   Example: 28, *-11, 61, 10, 55, *7, 280
        #   Example: 112, 31, 6, -47, 19, *-32, 181
        #   Example: 204, 163, 109, 53, 25, -37, 23, 51, *21, 126
        #   Example: 121, 44, 12, -26, *6, 322
        #   Example: 220, 141, 73, 46, 24, -39, 10, *-17, 191
        #   Example: 127, 58, 5, 2, *-79, 225, 224, 246, 232, 200

        for idx, row in enumerate(etas):
            is_arrived = False

            if 90 > last_tta >= row.tta or 30 >= row.tta:
                up = dn = 0
                sub_last_tta = row.tta
                for sub_row in etas[idx + 1:]:
                    if sub_row.tta > 120:  # large gap between TTA, probably next schedule
                        is_arrived = True
                        break
                    up += sub_row.tta >= sub_last_tta
                    dn += sub_row.tta < sub_last_tta
                    sub_last_tta = sub_row.tta
                    # u u * // (u u d) (u u u) OR d * * // (d d d) (d d u) (d u d) (d u u)
                    if dn == 0 and up > 1 or up == 0 and dn > 0:
                        break
                    if up + dn >= 3:
                        is_arrived = (up == 1 and dn == 2)  # u d d // (u d u)
                        break

            schedules.append((row.Index, row.eta))
            last_tta = row.tta
            last_timestamp = row.data_timestamp

            if is_arrived:
                for index, eta in schedules:
                    error = (eta - last_timestamp).total_seconds()
                    if math.isnan(error) or abs(error) > 7200:
                        # 1. malformated timestamp will result int float('nan')
                        # 2. ignore unusual TTA
                        continue
                    df.loc[index, ['accuracy']] = round(error / 60)
                schedules = []
                last_tta, last_timestamp = float('inf'), None
    return df


def _ml_dataset_clean_n_join(df: pd.DataFrame, filepath: Path) -> None:
    _calculate_etas_error(df) \
        .drop(columns=['dir', 'eta', 'data_timestamp'], errors='ignore') \
        .dropna(subset=['accuracy']) \
        .to_csv(filepath, mode='a', index=False, header=not filepath.exists())


def _kmb_raw_2_dataset_worker(route: str, raw_path: Path, out_dir: Path):
    df = pd.read_csv(raw_path,
                     on_bad_lines='warn',
                     low_memory=False,
                     index_col=[0])

    if len(df) == 0:
        # also aviod error: "Can only use .dt accessor with datetimelike values"
        return

    df[['eta', 'data_timestamp']] = df[['eta', 'data_timestamp']] \
        .apply(pd.to_datetime, format='ISO8601', cache=True, errors='coerce')
    df = df.assign(year=df['data_timestamp'].dt.year,
                   month=df['data_timestamp'].dt.month,
                   day=df['data_timestamp'].dt.day,
                   hour=df['data_timestamp'].dt.hour,
                   minute=df['data_timestamp'].dt.minute,
                   eta_hour=df['eta'].dt.hour,
                   eta_minute=df['eta'].dt.minute,
                   is_delayed=(df['rmk_en']
                               .str
                               .contains('Delayed journey', na=False)
                               .astype(int)),
                   is_scheduled=(df['rmk_en'] == 'Scheduled Bus').astype(int),
                   is_weekend=((df['data_timestamp'].dt.weekday >= 5)
                               .astype(int)),
                   tta=(df['eta'] - df['data_timestamp']).dt.total_seconds(),
                   accuracy=np.nan) \
        .drop(columns=['co', 'eta_seq', 'dest_tc', 'dest_sc', 'dest_en', 'weather',
                       'service_type', 'route', 'rmk_tc', 'rmk_sc', 'rmk_en',],
              errors='ignore') \
        .rename({'seq': 'stop'}, axis=1)

    _ml_dataset_clean_n_join(
        df[df['dir'] == 'O'], out_dir.joinpath(f'{route}_outbound.csv'))
    _ml_dataset_clean_n_join(
        df[df['dir'] == 'I'], out_dir.joinpath(f'{route}_inbound.csv'))


def _mtr_raw_2_dataset_worker(route: str, raw_path: Path, out_dir: Path):
    df = pd.read_csv(raw_path,
                     on_bad_lines='warn',
                     low_memory=False,
                     index_col=[0])

    if len(df) == 0:
        # also aviod error: "Can only use .dt accessor with datetimelike values"
        return

    df[['eta', 'data_timestamp']] = df[['eta', 'data_timestamp']] \
        .apply(pd.to_datetime, format='ISO8601', cache=True, errors='coerce')
    df = df.assign(stop=df['stop'].str.split('-').str.get(1).str.extract(r'(\d+)').astype(int),
                   year=df['data_timestamp'].dt.year,
                   month=df['data_timestamp'].dt.month,
                   day=df['data_timestamp'].dt.day,
                   hour=df['data_timestamp'].dt.hour,
                   minute=df['data_timestamp'].dt.minute,
                   eta_hour=df['eta'].dt.hour,
                   eta_minute=df['eta'].dt.minute,
                   is_weekend=(
                       df['data_timestamp'].dt.weekday >= 5).astype(int),
                   tta=(df['eta'] - df['data_timestamp']).dt.total_seconds(),
                   accuracy=''
                   ) \
        .drop(columns=['route', 'eta_seq'], errors='ignore')

    _ml_dataset_clean_n_join(
        df[df['dir'] == 'O'], out_dir.joinpath(f'{route}_outbound.csv'))
    _ml_dataset_clean_n_join(
        df[df['dir'] == 'I'], out_dir.joinpath(f'{route}_inbound.csv'))


class Predictor(ABC):

    __path_prefix__: str

    def __init__(self, data_dir: os.PathLike[str], transport_: transport.Transport) -> None:
        self.transport_ = transport_
        self.root_dir = Path(str(data_dir)) \
            .joinpath(self.__path_prefix__ or self.__class__.__name__.lower())
        self.raws_dir = self.root_dir.joinpath('raws')

        if not self.root_dir.exists():
            os.makedirs(self.root_dir)
        if not self.raws_dir.exists():
            os.makedirs(self.raws_dir)


class KmbPredictor(Predictor):

    __path_prefix__ = 'kmb'
    _RAW_HEADS = {
        'co': np.str_,
        'seq': np.int8,
        'dir': np.str_,
        'service_type': np.int8,
        'dest_en': np.str_,
        'eta_seq': np.int8,
        'eta': np.str_,
        'rmk_en': np.str_,
        'data_timestamp': np.str_
    }

    def predict(self,
                route_no: str,
                direction: enums.Direction,
                seq: int,
                data_timestamp: datetime,
                eta: datetime,
                rmk_en: str) -> list[Optional[int]]:
        try:
            df = pd.read_csv(self.root_dir.joinpath(f'{route_no}_{direction.value}.csv'),
                             low_memory=False)
            if len(df) == 0:
                return [None]
        except FileNotFoundError:
            return [None]

        model = sklearn.tree.DecisionTreeClassifier()
        model.fit(df.iloc[:, 0:-2].values, df.iloc[:, -1].values)
        return model.predict([[
            seq,
            data_timestamp.year,
            data_timestamp.month,
            data_timestamp.day,
            data_timestamp.hour,
            data_timestamp.minute,
            eta.hour,
            eta.minute,
            'Delayed journey' in rmk_en,
            'Scheduled' in rmk_en,
            data_timestamp.weekday() >= 5,
        ]])

    async def fetch_dataset(self) -> None:
        async def eta_with_route(r: str, s: aiohttp.ClientSession) -> tuple[str, list]:
            try:
                return r, (await api_async.kmb_eta(r, 1, s))['data']
            except (aiohttp.ClientError, asyncio.TimeoutError):
                return r, []

        async with aiohttp.ClientSession() as s:
            responses = await asyncio.gather(
                *[eta_with_route(r, s) for r in self.transport_.routes.keys()])

        # NOTE: using context manager with multiprocessing.Pool and uvicorn will cause uvicorn to restart
        with Pool(context=SpawnContext()) as pool:
            pool.starmap(_write_raw_csv_worker,
                         ((self.raws_dir.joinpath(f'{route_no}.csv'), self._RAW_HEADS, etas)
                             for route_no, etas in responses))

    def raws_to_ml_dataset(self, type_: Literal['day', 'night']) -> None:
        if type_ != 'day' and type_ != 'night':
            raise ValueError(f'Incorrect type: {type_}.')

        for fname in glob.glob('*.csv', root_dir=self.raws_dir):
            if (type_ == 'day' and fname.startswith('N')
                    or type_ == 'night' and not fname.startswith('N')
                    or '_copy' in fname):
                continue
            os.replace(self.raws_dir.joinpath(fname),
                       self.raws_dir.joinpath(f'{fname.removesuffix(".csv")}_copy.csv'))

        raw_paths = glob.glob('*_copy.csv', root_dir=self.raws_dir)

        # NOTE: using context manager with multiprocessing.Pool and uvicorn will cause uvicorn to restart
        with Pool(maxtasksperchild=20, context=SpawnContext()) as pool:
            pool.starmap(_kmb_raw_2_dataset_worker,
                         ((Path(filepath.replace('_copy', '')).stem,
                           self.raws_dir.joinpath(filepath),
                           self.root_dir)
                          for filepath in raw_paths))

        for path in raw_paths:
            os.remove(self.raws_dir.joinpath(path))


class MtrBusPredictor(Predictor):

    __path_prefix__ = 'mtr_bus'
    _RAW_HEADS = {
        'route': np.str_,
        'stop': np.str_,
        'dir': np.str_,
        'eta_seq': np.int8,
        'eta': np.str_,
        'data_timestamp': np.str_
    }

    def predict(self,
                route_no: str,
                direction: enums.Direction,
                stop_code: str,
                data_timestamp: datetime,
                eta: datetime) -> list[Optional[int]]:
        try:
            df = pd.read_csv(self.root_dir.joinpath(f'{route_no}_{direction.value}.csv'),
                             low_memory=False)
            if len(df) == 0:
                return [None]
        except FileNotFoundError:
            return [None]

        model = sklearn.tree.DecisionTreeClassifier()
        model.fit(df.iloc[:, 0:-2].values, df.iloc[:, -1].values)
        return model.predict([[
            ''.join(filter(str.isdigit, stop_code.split('-')[-1])),
            data_timestamp.year,
            data_timestamp.month,
            data_timestamp.day,
            data_timestamp.hour,
            data_timestamp.minute,
            eta.hour,
            eta.minute,
            data_timestamp.weekday() >= 5,
        ]])

    async def fetch_dataset(self) -> None:
        processed_etas = {}
        data_timestamp = datetime.now()  # timestamp from the API is not accurate enough
        async with aiohttp.ClientSession() as s:
            responses = await asyncio.gather(*[api_async.mtr_bus_eta(r, 'en', s)
                                             for r in self.transport_.route_list().keys()],
                                             return_exceptions=True)

        for route in responses:
            if isinstance(route, aiohttp.ClientError):
                continue
            processed_etas.setdefault(route['routeName'], [])
            for stop in route['busStop']:
                for idx, eta in enumerate(stop['bus']):
                    eta_second = int(eta['departureTimeInSecond']) \
                        if any(s in stop['busStopId'] for s in ('U010', 'D010')) \
                        else int(eta['arrivalTimeInSecond'])
                    dir_ = 'O' \
                        if stop['busStopId'].split('-')[1].startswith('U') \
                        else 'I'

                    processed_etas[route['routeName']].append({
                        'route': route['routeName'],
                        'stop': stop['busStopId'],
                        'dir': dir_,
                        'eta_seq': idx + 1,
                        'data_timestamp': data_timestamp.isoformat(timespec='seconds'),
                        'eta': (data_timestamp + timedelta(seconds=eta_second)).isoformat(timespec='seconds')
                    })

        # relativly fast processing time, no need for multiprocessing
        for route_no, etas in processed_etas.items():
            _write_raw_csv_worker(self.raws_dir.joinpath(f'{route_no}.csv'),
                                  self._RAW_HEADS,
                                  etas)

    def raws_to_ml_dataset(self, type_: Literal['day', 'night']) -> None:
        if type_ == 'night':
            return
        if type_ != 'day':
            raise ValueError(f'Incorrect type: {type_}.')

        for fname in glob.glob('*.csv', root_dir=self.raws_dir):
            os.replace(self.raws_dir.joinpath(fname),
                       self.raws_dir.joinpath(f'{fname.removesuffix(".csv")}_copy.csv'))

        raw_paths = glob.glob('*_copy.csv', root_dir=self.raws_dir)

        # NOTE: using context manager with multiprocessing.Pool and uvicorn will cause uvicorn to restart
        with Pool(context=SpawnContext()) as pool:
            pool.starmap(_mtr_raw_2_dataset_worker,
                         ((Path(filepath.replace('_copy', '')).stem,
                           self.raws_dir.joinpath(filepath),
                           self.root_dir)
                          for filepath in raw_paths))

        for path in raw_paths:
            os.remove(self.raws_dir.joinpath(path))
