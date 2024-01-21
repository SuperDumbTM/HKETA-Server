import asyncio
import json
import math
import os
from datetime import datetime
from multiprocessing.pool import Pool, ThreadPool
from pathlib import Path
from typing import Literal, Optional

import aiohttp
import pandas as pd
import pytz
import sklearn.tree

try:
    from app.src.modules.hketa import api, api_async
except (ImportError, ModuleNotFoundError):
    import api
    import api_async


class KmbPredictor:

    _HEADS = ['co', 'route', 'dir', 'service_type', 'seq', 'dest_tc', 'dest_sc',
              'dest_en', 'eta_seq', 'eta', 'rmk_tc', 'rmk_sc', 'rmk_en', 'data_timestamp']

    def __init__(self, directory: os.PathLike[str],) -> None:
        self.root_dir = Path(str(directory))
        if not self.root_dir.exists():
            self.root_dir.mkdir()

    def predict(self,
                route: str,
                seq: int,
                data_timestamp: datetime,
                eta: datetime,
                rmk_en: str) -> Optional[int]:
        path = self.root_dir.joinpath(f'{route}.csv')
        if not path.exists():
            return None

        df = pd.read_csv(path)
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

    def fetch_dataset(self) -> None:
        def entry_cleaning(eta: dict) -> dict:
            try:
                # malformed data_timestamp is save to be replaced by the current time
                # while eta not, which will be ignore later at `process_raw_dataset`
                datetime.fromisoformat(eta['data_timestamp'])
            except (ValueError, TypeError):
                eta['data_timestamp'] = datetime.now(
                    pytz.timezone('Asia/Hong_kong')).isoformat(timespec='seconds')

            return eta

        with open(Path(__file__).parent.joinpath('kmb.json'), 'r', encoding='utf-8') as f:
            routes = json.load(f)

        with ThreadPool(15) as pool:
            results = pool.map(
                lambda p: api.kmb_eta(*p)['data'], [(r, 1) for r in routes])

        filename = self.root_dir.joinpath('raws.csv')
        if not os.path.exists(filename):
            old_df = pd.DataFrame(columns=self._HEADS)
        else:
            old_df = pd.read_csv(filename, index_col=0)

        df = pd.DataFrame(
            [entry_cleaning(eta)
                for eta in (eta for route in results for eta in route)
                if eta['eta'] is not None],
            columns=self._HEADS)

        pd.concat([old_df, df[df['eta_seq'] == 1]]) \
            .reset_index(drop=True) \
            .to_csv(filename, mode='w', index=True)

    async def fetch_dataset_async(self) -> None:
        def entry_cleaning(eta: dict) -> dict:
            try:
                # malformed data_timestamp is save to be replaced by the current time
                # while eta not, which will be ignore later at `process_raw_dataset`
                datetime.fromisoformat(eta['data_timestamp'])
            except (ValueError, TypeError):
                eta['data_timestamp'] = datetime.now(
                    pytz.timezone('Asia/Hong_kong')).isoformat(timespec='seconds')

            return eta

        with open(Path(__file__).parent.joinpath('kmb.json'), 'r', encoding='utf-8') as f:
            routes = json.load(f)

        async with aiohttp.ClientSession() as s:
            results = await asyncio.gather(*[
                api_async.kmb_eta(r, 1, s) for r in routes
            ])

        filename = self.root_dir.joinpath('raws.csv')
        if not os.path.exists(filename):
            old_df = pd.DataFrame(columns=self._HEADS)
        else:
            old_df = pd.read_csv(filename, index_col=0)

        df = pd.DataFrame(
            [entry_cleaning(eta)
                for eta in (eta for route in results for eta in route['data'])
                if eta['eta'] is not None],
            columns=self._HEADS)

        pd.concat([old_df, df[df['eta_seq'] == 1]]) \
            .reset_index(drop=True) \
            .to_csv(filename, mode='w', index=True)

    def raws_to_ml_dataset(self, type_: Literal['day', 'night']) -> None:
        if type_ != 'day' or type_ != 'night':
            raise ValueError(f'Incorrect type: {type_}.')

        df = pd.read_csv(self.root_dir.joinpath('raws.csv'),
                         on_bad_lines='warn',
                         low_memory=False,
                         index_col=[0])

        day_routes = df[~df['route'].str.startswith('N')]
        night_routes = df[df['route'].str.startswith('N')]

        if type_ == 'day':
            df = day_routes
            night_routes.to_csv(self.root_dir.joinpath(
                'raws.csv'), mode='w', index=True)
        else:
            df = night_routes
            day_routes.to_csv(self.root_dir.joinpath(
                'raws.csv'), mode='w', index=True)

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
                       # second=df['data_timestamp'].dt.second,
                       eta_hour=df['eta'].dt.hour,
                       eta_minute=df['eta'].dt.minute,
                       # eta_second=df['eta'].dt.second,
                       is_scheduled=(df['rmk_en'] ==
                                     'Scheduled Bus').astype(int),
                       is_weekend=(
                           df['data_timestamp'].dt.weekday >= 5).astype(int),
                       tta=(df['eta'] - df['data_timestamp']
                            ).dt.total_seconds(),
                       accuracy='') \
            .drop(columns=['co', 'eta_seq', 'dest_tc', 'dest_sc', 'dest_en', 'weather',
                           'service_type', 'route', 'rmk_tc', 'rmk_sc', 'rmk_en',],
                  errors='ignore')

        self._generate_ml_dataset(
            df[df['dir'] == 'O'], self.root_dir.joinpath(f'{route}_outbound.csv'))
        self._generate_ml_dataset(
            df[df['dir'] == 'I'], self.root_dir.joinpath(f'{route}_inbound.csv'))

    def _generate_ml_dataset(self, df: pd.DataFrame, filename: os.PathLike) -> None:
        self._calculate_etas_error(df) \
            .drop(columns=['dir', 'eta', 'data_timestamp'], errors='ignore') \
            .drop(df[df['accuracy'] == ''].index, errors='ignore') \
            .to_csv(filename, mode='a', index=False)

    def _calculate_etas_error(self, df: pd.DataFrame) -> pd.DataFrame:
        for _, group in df.groupby('seq'):
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

    def _append_dataset(self, new_df: pd.DataFrame, filename: os.PathLike) -> pd.DataFrame:
        df = pd.read_csv(self.root_dir.joinpath(str(filename)))

        if len(df['month'].unique()) > 3:
            del_y = sorted(df['year'].unique())[0]
            del_m = sorted(df[df['year'].eq(del_y)]['month'].unique())[0]
            del_d = sorted(
                df.loc[df['month'].eq(del_m) & df['year'].eq(del_y)]['day'].unique())[0]
            df = df.drop(
                df[df['year'].eq(del_y) & df['month'].eq(del_m) & df['day'].eq(del_d)].index)

        return pd.concat([df, new_df])
