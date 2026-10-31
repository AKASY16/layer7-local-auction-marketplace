"""Read-only references; shared B03/B04 counted once, unsupported errors omitted."""
import json
import hashlib
import sys
import zlib
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
DEST=ROOT/'validation/v2_choice/results/references.json'


def main():
    data=Path.home()/'Desktop/Data/Jank & Shmueli'
    files=[data/'Cartier wristwatched on eBay/Cartier+3-day+auctions.csv',
           data/'Palm Pilot M515 PDAs on eBay/Palm+3-day+auctions.csv',
           data/'Xbox game consoles on eBay/Xbox 3-day auctions.csv']
    frames=[pd.read_csv(p) for p in files]
    d=pd.concat(frames,ignore_index=True)
    d=d[d.auctionid.map(lambda x:zlib.crc32(str(x).encode())%1000<300)].copy()
    d=d[d.bidder.notna()]
    groups=d.groupby('auctionid')
    pairs=d.groupby(['auctionid','bidder']).size()
    js={'n_positive_auctions':d.auctionid.nunique(),'n_pairs':len(pairs),
        'js3_bidders_mean_pos':float(groups.bidder.nunique().mean()),
        'js3_bids_per_pair':float(pairs.mean()),'js3_repeat_pair_share':float(pairs.ge(2).mean()),
        'group':'jank_shmueli','status':'Same definitions and72h positive-bid conditioning; different goods/market. Previously known holdout, not a fresh preregistered test.'}
    folder=ROOT/'data/external/end_time_recommendation/podwol_schneider_shared/b04_2rf7n9mwwk'
    p=next(folder.glob('*.dta'))
    raw=pd.read_stata(p,convert_categoricals=False)
    f=raw[raw.morebids.eq(0)].copy()
    f=f[f.shipcost.notna()&f.shipcost.le(10)&f.hasreserve.ne(1)&f.auction.eq(1)&f.itemnew.eq(1)]
    assert len(f)==1563
    duration=f.auctionendtimenum-f.auctionstarttimenum
    f=f[duration.between(1-1e-6,3+1e-6)]
    sold=f.endprice.gt(0)
    prices=f.loc[sold,'endprice']+f.loc[sold,'shipcost']
    b04={'n_auctions':len(f),'n_sold':int(sold.sum()),'b04_bidders_mean':float(f.numberofbidders.mean()),
         'b04_sold_rate':float(sold.mean()),'b04_sold_log_price_sd':float(np.std(np.log(prices),ddof=1)),
         'group':'podwol_schneider_shared','status':'New auctions,24-72h range, includes unsold. Duration mixture/goods/supply differ: external-transfer diagnostic, not LAYER7 truth.',
         'B03_independent_evidence':False,'price_error_allowed':False,
         'note':'No raw USD/KRW mean error or bidder migration from94.2% masked IDs.'}
    # Reuse earlier verified A-01 aggregates; do not recompute an arbitrary new fit.
    prior=Path(r'C:\Users\USER\Documents\Codex\2026-10-29\https-github-com-akasy16-layer7-local\outputs\new-materials-model-review-2026-10-31\evidence\a01_analysis.json')
    a=json.loads(prior.read_text(encoding='utf-8'))
    a01={'group':'a01_bidders_curse','multi_auction_bidder_share':a['share_bidders_seen_in_multiple_auctions'],
         'switch_rate':a['switches_to_another_auction']/a['within_bidder_consecutive_transitions'],
         'open_switch_share':a['switches_while_previous_auction_open']/a['switches_to_another_auction'],
         'error_allowed':False,'status':'Different observation horizon/single product/selected history/ties. Descriptive reference only; no matching to22% target.'}
    proxy={'log_price_sd_figure':.846,'log_price_sd_limited_goods':.894,'log_price_sd_retro_game':1.367,
           'status':'Previously used cross-product proxies; scale-free sold price spread only; NOT identified intrinsic WTP. Excluded from direct-validation adoption score.'}
    source_files={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files+[p,prior]}
    result={'JS3_holdout':js,'B04_shared_matched':b04,'A01_descriptive':a01,'price_transfer_proxies':proxy,
            'file_sha256':source_files,'no_tuning':True}
    if DEST.exists():raise FileExistsError(DEST)
    DEST.parent.mkdir(parents=True,exist_ok=True)
    DEST.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(result,indent=2,ensure_ascii=False))


if __name__=='__main__':main()
