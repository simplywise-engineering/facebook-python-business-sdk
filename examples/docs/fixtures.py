# Copyright 2014 Facebook, Inc.

# You are hereby granted a non-exclusive, worldwide, royalty-free license to
# use, copy, modify, and distribute this software in source code or binary
# form for use in connection with the web services and APIs provided by
# Facebook.

# As with any software that integrates with the Facebook platform, your use
# of this software is subject to the Facebook Developer Principles and
# Policies [http://developers.facebook.com/policy/]. This copyright notice
# shall be included in all copies or substantial portions of the software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

from facebookads import (
    exceptions,
    test_config,
    FacebookAdsApi,
    FacebookSession
)
from facebookads.objects import (
    AdAccount,
    AdCampaign,
    AdVideo,
    AdImage,
    AdSet,
    AdsPixel,
    AdCreative,
    AdGroup,
    CustomAudience
)
from facebookads.specs import LinkData, ObjectStorySpec

import time
import atexit

default_api_url = 'https://graph.facebook.com/' + FacebookAdsApi.API_VERSION
default_campaign_params = {
    AdCampaign.Field.name: 'Test Campaign',
    AdCampaign.Field.buying_type: AdCampaign.BuyingType.auction,
    AdCampaign.Field.objective: AdCampaign.Objective.none,
    AdCampaign.Field.status: AdCampaign.Status.paused,
}


def api_get(path, api=None, url=default_api_url):
    if api is None:
        api = FacebookAdsApi.get_default_api()
    response = api.call('GET', url + path)
    return response.json()


def api_post(path, params={}, api=None, url=default_api_url):
    if api is None:
        api = FacebookAdsApi.get_default_api()
    response = api.call('POST', url + path, **params)
    return response.json()


def get_page_access_token():
    data = api_get('/me/accounts')['data']
    for page in data:
        if page['id'] == str(test_config.page_id):
            return page['access_token']
    raise 'Page access token for page id {} not found.'.\
        format(test_config.page_id)


def get_page_api():
    page_token = get_page_access_token()
    session = FacebookSession(test_config.app_id,
                              test_config.app_secret,
                              page_token)
    return FacebookAdsApi(session)


def get_promotable_post():
    api = get_page_api()
    path = "/{}/promotable_posts".format(test_config.page_id)
    posts = api_get(path, api)['data']

    if len(posts) == 0:
        raise "Could not find any promotable posts on your page"

    return posts[0]


def upload_video(video_path):
    api = get_page_api()
    path = "/{}/videos".format(test_config.page_id)
    url = 'https://graph-video.facebook.com/' + FacebookAdsApi.API_VERSION

    return api_post(path,
                    {'files': {'source': open(video_path)}},
                    api,
                    url)


def remote_delete(obj):
    try:
        obj.remote_delete()
    except exceptions.FacebookRequestError:
        print("warning: could not delete {}".format(obj))


def delete_image(image):
    image_hash = image[AdImage.Field.hash]
    image_id = image[AdImage.Field.id]
    image = AdImage(image_id, test_config.account_id)
    image.remote_delete(params={AdImage.Field.hash: image_hash()})


def create_adcampaign(params={}):
    campaign_params = default_campaign_params.copy()
    campaign_params.update(params)

    campaign = AdCampaign(parent_id=test_config.account_id)
    campaign.update(campaign_params)
    campaign.remote_create()

    atexit.register(remote_delete, campaign)

    return campaign


def create_image():
    image = AdImage(parent_id=test_config.account_id)
    image[AdImage.Field.filename] = test_config.image_path
    image.remote_create()

    # FIXLATER: properly delete images with dependencies

    return image


def create_video():
    video = AdVideo(parent_id=test_config.account_id)
    video[AdVideo.Field.filepath] = test_config.video_path
    video.remote_create()
    video.waitUntilEncodingReady()

    atexit.register(remote_delete, video)

    return video


def unique_name(base_name):
    return base_name + ' ' + str(time.clock())


def create_creative(image=create_image()):
    image_hash = image.get_hash()

    link_data = LinkData()
    link_data[LinkData.Field.message] = 'try it out'
    link_data[LinkData.Field.link] = 'http://example.com'
    link_data[LinkData.Field.caption] = 'www.example.com'
    link_data[LinkData.Field.image_hash] = image_hash

    object_story_spec = ObjectStorySpec()
    object_story_spec[ObjectStorySpec.Field.page_id] = test_config.page_id
    object_story_spec[ObjectStorySpec.Field.link_data] = link_data

    creative = AdCreative(parent_id=test_config.account_id)
    creative[AdCreative.Field.name] = unique_name('Test Creative')
    creative[AdCreative.Field.object_story_spec] = object_story_spec
    creative.remote_create()

    atexit.register(remote_delete, creative)

    return creative


def create_custom_audience():
    audience = CustomAudience(parent_id=test_config.account_id)
    audience[CustomAudience.Field.subtype] = CustomAudience.Subtype.custom
    audience[CustomAudience.Field.name] = 'Test Audience'
    audience[CustomAudience.Field.description] = 'Created for docsmith example'
    audience.remote_create()

    atexit.register(remote_delete, audience)

    return audience


def create_ads_pixel():
    account = AdAccount(test_config.account_id)
    pixel = account.get_ads_pixels([AdsPixel.Field.code])

    if pixel is None:
        pixel = AdsPixel(parent_id=test_config.account_id)
        pixel[AdsPixel.Field.name] = 'Test Pixel'
        pixel.remote_create()

    return pixel


def create_adset(campaign=create_adcampaign()):
    adset = AdSet(parent_id=test_config.account_id)
    adset[AdSet.Field.name] = 'Test Adset'
    adset[AdSet.Field.campaign_group_id] = campaign.get_id()
    adset[AdSet.Field.targeting] = {
        'geo_locations': {
            'countries': ['US']
        }
    }
    adset[AdSet.Field.optimization_goal] = AdSet.OptimizationGoal.impressions
    adset[AdSet.Field.billing_event] = AdSet.BillingEvent.impressions
    adset[AdSet.Field.bid_amount] = 100
    adset[AdSet.Field.daily_budget] = 1000
    adset.remote_create()

    atexit.register(remote_delete, adset)

    return adset


def create_adgroup(ad_set=create_adset(), creative=create_creative()):
    adgroup = AdGroup(parent_id=test_config.account_id)
    adgroup[AdGroup.Field.name] = 'My AdGroup'
    adgroup[AdGroup.Field.campaign_id] = ad_set.get_id_assured()
    adgroup[AdGroup.Field.status] = AdGroup.Status.paused
    adgroup[AdGroup.Field.creative] = {
        'creative_id': creative.get_id_assured(),
    }
    adgroup.remote_create()

    atexit.register(remote_delete, adgroup)

    return adgroup