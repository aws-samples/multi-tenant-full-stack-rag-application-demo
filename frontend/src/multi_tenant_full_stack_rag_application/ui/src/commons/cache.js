import { Cache } from 'aws-amplify';
export function setCache(key, value, ttl=60*60*24*7) {
    let expTime=new Date().getTime() + ttl
    Cache.setItem(key, value, { expires: expTime });
}

export function getCache(key, callbackFn={}) {
    Cache.getItem(key, {callback: callbackFn});
}

