// Copyright 2017 ETH Zurich
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//   http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package control

import "github.com/netsec-ethz/scion/go/sig/base"

type StaticRP struct {
	SDB    *base.Topology
	File   string
	Routes map[string]string
	Device string
}

func NewStaticRP(sdb *base.Topology) *StaticRP {
	return &StaticRP{SDB: sdb}
}

func (rp *StaticRP) AddRoute(destination string, isdas string) error {
	return rp.SDB.AddRoute(destination, isdas)
}

func (rp *StaticRP) DelRoute(destination string, isdas string) error {
	return rp.SDB.DelRoute(destination, isdas)
}

func (rp *StaticRP) AddSig(isdas string, encapAddr string, encapPort string, ctrlAddr string, ctrlPort string) error {
	return rp.SDB.AddSig(isdas, encapAddr, encapPort, ctrlAddr, ctrlPort, "static")
}

func (rp *StaticRP) DelSig(isdas string, address string, port string) error {
	return rp.SDB.DelSig(isdas, address, port, "static")
}

func (rp *StaticRP) Print() string {
	return rp.SDB.Print("static")
}
