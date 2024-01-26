from abc import ABC, abstractmethod
import asyncio
import glob
import math
import os
from datetime import datetime, timedelta
from multiprocessing.pool import Pool
from pathlib import Path
from typing import Literal, Optional

import aiohttp
import pandas as pd
import sklearn.tree

try:
    from app.src.modules.hketa import api_async, transport
except (ImportError, ModuleNotFoundError):
    import api_async
    import transport


def _write_raw_csv_worker(path: Path, headers: list[str], etas: list) -> None:
    if not os.path.exists(path):
        old_df = pd.DataFrame(columns=headers)
    else:
        old_df = pd.read_csv(path, index_col=0, low_memory=True)

    df = pd.DataFrame([eta for eta in etas if eta['eta'] is not None],
                      columns=headers,)

    if len(df) == 0:
        return
    pd.concat([old_df, df[df['eta_seq'] == 1]]) \
        .reset_index(drop=True) \
        .to_csv(path, mode='w', index=True)


def _calculate_etas_error(df: pd.DataFrame) -> pd.DataFrame:
    for _, group in df.groupby('stop'):
        schedules = []
        last_tta, last_timestamp = float('inf'), None

        for row in group.itertuples():
            if row.tta > last_tta:
                for index, eta in schedules:
                    error = (eta - last_timestamp).total_seconds()
                    if math.isnan(error) or abs(error) > 7200:
                        # 1. malformated timestamp will result int float('nan')
                        # 2. ignore unusual TTA
                        continue
                    df.loc[index, ['accuracy']] = round(error / 60)
                schedules = []
                last_tta, last_timestamp = float('inf'), None

            schedules.append((row.Index, row.eta))
            last_tta = row.tta
            last_timestamp = row.data_timestamp
    return df


def _ml_dataset_clean_n_join(df: pd.DataFrame, filepath: Path) -> None:
    _calculate_etas_error(df) \
        .drop(columns=['dir', 'eta', 'data_timestamp'], errors='ignore') \
        .drop(df[df['accuracy'] == ''].index, errors='ignore') \
        .to_csv(filepath, mode='a', index=False, header=not filepath.exists())


def _kmb_raw_2_dataset_worker(route: str, raw_path: Path, out_dir: Path):
    df = pd.read_csv(raw_path,
                     on_bad_lines='warn',
                     low_memory=False,
                     index_col=[0])

    df[['eta', 'data_timestamp']] = df[['eta', 'data_timestamp']] \
        .apply(pd.to_datetime, format='ISO8601', cache=True, errors='coerce')

    df = df.assign(year=df['data_timestamp'].dt.year,
                   month=df['data_timestamp'].dt.month,
                   day=df['data_timestamp'].dt.day,
                   hour=df['data_timestamp'].dt.hour,
                   minute=df['data_timestamp'].dt.minute,
                   # second=raw['data_timestamp'].dt.second,
                   eta_hour=df['eta'].dt.hour,
                   eta_minute=df['eta'].dt.minute,
                   # eta_second=raw['eta'].dt.second,
                   is_scheduled=(df['rmk_en'] ==
                                 'Scheduled Bus').astype(int),
                   is_weekend=(
        df['data_timestamp'].dt.weekday >= 5).astype(int),
        tta=(df['eta'] - df['data_timestamp']
             ).dt.total_seconds(),
        accuracy='') \
        .drop(columns=['co', 'eta_seq', 'dest_tc', 'dest_sc', 'dest_en', 'weather',
                       'service_type', 'route', 'rmk_tc', 'rmk_sc', 'rmk_en',],
              errors='ignore') \
        .rename({'seq': 'stop'}, axis=1)

    _ml_dataset_clean_n_join(
        df[df['dir'] == 'O'], out_dir.joinpath(f'{route}_outbound.csv'))
    _ml_dataset_clean_n_join(
        df[df['dir'] == 'I'], out_dir.joinpath(f'{route}_inbound.csv'))


class Predictor(ABC):

    __path_prefix__: str

    def __init__(self, directory: os.PathLike[str], transport_: transport.Transport) -> None:
        self.transport_ = transport_
        self.root_dir = Path(str(directory)) \
            .joinpath(self.__path_prefix__ or self.__class__.__name__.lower())
        self.raws_dir = self.root_dir.joinpath('raws')

        if not self.root_dir.exists():
            os.makedirs(self.root_dir)
        if not self.raws_dir.exists():
            os.makedirs(self.raws_dir)

    def _calculate_etas_error(self, df: pd.DataFrame) -> pd.DataFrame:
        for _, group in df.groupby('stop'):
            schedules = []
            last_tta, last_timestamp = float('inf'), None

            for row in group.itertuples():
                if row.tta > last_tta:
                    for index, eta in schedules:
                        error = (eta - last_timestamp).total_seconds()
                        if math.isnan(error) or abs(error) > 7200:
                            # 1. malformated timestamp will result int float('nan')
                            # 2. ignore unusual TTA
                            continue
                        df.loc[index, ['accuracy']] = round(error / 60)
                    schedules = []
                    last_tta, last_timestamp = float('inf'), None

                schedules.append((row.Index, row.eta))
                last_tta = row.tta
                last_timestamp = row.data_timestamp
        return df


class KmbPredictor(Predictor):

    __path_prefix__ = 'kmb'
    _HEADS = ['co', 'route', 'dir', 'service_type', 'seq', 'dest_tc', 'dest_sc',
              'dest_en', 'eta_seq', 'eta', 'rmk_tc', 'rmk_sc', 'rmk_en', 'data_timestamp']

    def predict(self,
                route: str,
                seq: int,
                data_timestamp: datetime,
                eta: datetime,
                rmk_en: str) -> Optional[int]:
        path = self.root_dir.joinpath(f'{route}.csv')
        if not path.exists():
            return None

        df = pd.read_csv(path, low_memory=True)
        values = [{
            'seq': seq,
            'year': data_timestamp.year,
            'month': data_timestamp.month,
            'day': data_timestamp.day,
            'hour': data_timestamp.hour,
            'minute': data_timestamp.minute,
            'eta_hour': eta.hour,
            'eta_minute': eta.minute,
            'is_schedule': 'Scheduled' in rmk_en,
            'is_weekend': data_timestamp.weekday() >= 5
        }]

        model = sklearn.tree.DecisionTreeClassifier()
        model.fit(df.values[:-2], df.values[:-1])
        return model.predict(values)

    async def fetch_dataset(self) -> None:
        async def eta_with_route(r: str, s: aiohttp.ClientSession):
            return r, (await api_async.kmb_eta(r, 1, s))['data']

        async with aiohttp.ClientSession() as s:
            results = await asyncio.gather(*[
                eta_with_route(r, s) for r in self.transport_.routes.keys()
            ])

        import time
        with Pool(os.cpu_count() or 4, maxtasksperchild=50) as pool:
            for i in range(1080):
                start = time.time()
                pool.starmap(_write_raw_csv_worker,
                             ((self.raws_dir.joinpath(f'{r}.csv'), self._HEADS, data) for r, data in results))
                print(f'@{i}:\t{time.time() - start}')

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
        with Pool(os.cpu_count() or 4) as pool:
            pool.starmap(_kmb_raw_2_dataset_worker,
                         [(Path(fn.replace('_copy', '')).stem, self.raws_dir.joinpath(fn), self.root_dir)
                          for fn in raw_paths])

        for path in raw_paths:
            os.remove(self.raws_dir.joinpath(path))


class MtrBusPredictor(Predictor):

    __path_prefix__ = 'mtr_bus'
    _HEADS = ['route', 'dir', 'eta_seq', 'stop', 'eta', 'data_timestamp']

    async def fetch_dataset(self) -> None:
        filename = self.raws_dir.joinpath('raws.csv')
        if not os.path.exists(filename):
            old_df = pd.DataFrame(columns=self._HEADS)
        else:
            old_df = pd.read_csv(filename, index_col=0, low_memory=True)

        async with aiohttp.ClientSession() as e:
            all_eta = await asyncio.gather(
                *[api_async.mtr_bus_eta(r, 'en', e) for r in self.transport_.route_list().keys()])

        etas = []
        data_timestamp = datetime.now()
        for route in all_eta:
            for stop in route['busStop']:
                for idx, eta in enumerate(stop['bus']):
                    eta_second = int(eta['departureTimeInSecond']) \
                        if any(s in stop['busStopId'] for s in ('U010', 'D010')) \
                        else int(eta['arrivalTimeInSecond'])
                    dir_ = 'O' \
                        if stop['busStopId'].split('-')[1].startswith('U') \
                        else 'I'

                    etas.append({
                        'route': route['routeName'],
                        'stop': stop['busStopId'],
                        'dir': dir_,
                        'eta_seq': idx + 1,
                        'data_timestamp': data_timestamp.isoformat(timespec='seconds'),
                        'eta': (data_timestamp + timedelta(seconds=eta_second)).isoformat(timespec='seconds')
                    })

        df = pd.DataFrame(etas, columns=self._HEADS)
        pd.concat([old_df, df[df['eta_seq'] == 1]]) \
            .reset_index(drop=True) \
            .to_csv(filename, mode='w', index=True)

    def raws_to_ml_dataset(self, type_: Literal['day', 'night']) -> None:
        if type_ == 'night':
            return
        if type_ != 'day':
            raise ValueError(f'Incorrect type: {type_}.')

        os.replace(self.raws_dir.joinpath('raws.csv'),
                   self.raws_dir.joinpath('raws_copy.csv'))

        df = pd.read_csv(Path(__file__).parent.joinpath('raws_copy.csv'),
                         on_bad_lines='warn',
                         low_memory=False,
                         index_col=[0])

        with Pool(os.cpu_count() or 4) as pool:
            pool.starmap(self._process_raw_dataset,
                         [g for g in df.groupby('route')])

    def _process_raw_dataset(self, route: str, df: pd.DataFrame) -> None:
        df[['eta', 'data_timestamp']] = df[['eta', 'data_timestamp']] \
            .apply(pd.to_datetime, format='ISO8601', cache=True, errors='coerce')

        df = df.assign(year=df['data_timestamp'].dt.year,
                       month=df['data_timestamp'].dt.month,
                       day=df['data_timestamp'].dt.day,
                       hour=df['data_timestamp'].dt.hour,
                       minute=df['data_timestamp'].dt.minute,
                       eta_hour=df['eta'].dt.hour,
                       eta_minute=df['eta'].dt.minute,
                       is_weekend=(
            df['data_timestamp'].dt.weekday >= 5).astype(int),
            tta=(df['eta'] - df['data_timestamp']
                 ).dt.total_seconds(),
            accuracy='')

        _ml_dataset_clean_n_join(
            df[df['dir'] == 'O'], Path(__file__).parent.joinpath('mtr_bus', f'{route}_outbound.csv'))
        _ml_dataset_clean_n_join(
            df[df['dir'] == 'I'], Path(__file__).parent.joinpath('mtr_bus', f'{route}_inbound.csv'))
