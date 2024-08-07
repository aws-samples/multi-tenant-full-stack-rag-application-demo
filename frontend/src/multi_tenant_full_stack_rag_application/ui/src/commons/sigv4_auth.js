//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: MIT-0

import * as crt from "aws-crt";
import {HttpRequest} from "aws-crt/dist/native/http";

export function sigV4ASign(method, endpoint, config = crt.auth.AwsSigningConfig) {
    const host = new URL(endpoint).host;
    const request = new HttpRequest(method, endpoint);
    request.headers.add('host', host);

    crt.auth.aws_sign_request(request, config);
    return request.headers;
}

export function sigV4ASignBasic(method, endpoint, service, body={}, queryParameters={}) {
    const host = new URL(endpoint).host;
    const request = new HttpRequest(method, endpoint);
    request.headers.add('host', host);
    if (queryParameters !== {}) {
        request.headers.queryParameters = queryParameters
    }
    if (['POST','PUT'].includes(method)) {
        request.body = body
    }
    const config = {
        service: service,
        region: "*",
        algorithm: crt.auth.AwsSigningAlgorithm.SigV4Asymmetric,
        signature_type: crt.auth.AwsSignatureType.HttpRequestViaHeaders,
        signed_body_header: crt.auth.AwsSignedBodyHeaderType.XAmzContentSha256,
        provider: crt.auth.AwsCredentialsProvider.newDefault()
    };

    crt.auth.aws_sign_request(request, config);
    return request.headers;
}
