//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: MIT-0

// A blank react component that takes a signout function as a prop, and uses it to sign the user out. Then it redirects to the homepage
function SignOut({ signout }) {
    signout();
    location.href = '/';
    return (<></>);
}
export default SignOut;