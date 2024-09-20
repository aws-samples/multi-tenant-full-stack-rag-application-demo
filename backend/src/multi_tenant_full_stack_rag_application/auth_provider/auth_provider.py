#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

from abc import ABC, abstractmethod

class AuthProvider(ABC):   
   
    @abstractmethod
    def get_userid_from_token(self, auth_token, origin):
        pass
